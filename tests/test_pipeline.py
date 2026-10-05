"""Unit tests for the pure data-shaping logic (no network, no S3)."""

import importlib

import pandas as pd

from scripts import common, config, espn

table_progression = importlib.import_module("scripts.03_build_table_progression")
player_stats = importlib.import_module("scripts.04_fetch_player_stats")
matches_mod = importlib.import_module("scripts.02_fetch_matches")
toplines = importlib.import_module("scripts.07_create_toplines_summary")
matchday = importlib.import_module("scripts.10_post_matchday")


def espn_event(event_id, date, us_home, us_score, them_score, opp_id="1", completed=True):
    us = {'id': config.ESPN_TEAM_ID, 'homeAway': 'home' if us_home else 'away',
          'team': {'displayName': 'Fulham', 'abbreviation': 'FUL'},
          'score': {'value': us_score, 'displayValue': str(us_score)}}
    them = {'id': opp_id, 'homeAway': 'away' if us_home else 'home',
            'team': {'displayName': f'Team {opp_id}', 'abbreviation': f'T{opp_id}'},
            'score': {'value': them_score, 'displayValue': str(them_score)}}
    return {'id': event_id, 'date': date, 'competitions': [{
        'competitors': [us, them], 'venue': {'fullName': 'Craven Cottage'},
        'status': {'type': {'name': 'STATUS_FULL_TIME' if completed else 'STATUS_SCHEDULED',
                            'completed': completed}}}]}


def test_parse_event_from_fulham_point_of_view():
    row = espn.parse_event(espn_event('10', '2026-08-24T19:00Z', us_home=False, us_score=2, them_score=1))
    assert row['home_away'] == 'away'
    assert (row['goals_for'], row['goals_against'], row['result'], row['points']) == (2, 1, 'W', 3)
    assert row['date'] == '2026-08-24' and row['kickoff_local'] == '20:00'  # BST


def test_parse_event_upcoming_has_no_score():
    row = espn.parse_event(espn_event('11', '2026-12-26T15:00Z', True, 0, 0, completed=False))
    assert row['result'] is None and row['goals_for'] is None
    assert row['kickoff_local'] == '15:00'  # GMT


def test_dedupe_keeps_original_event_per_pairing():
    rows = [
        {'event_id': '678029', 'opponent_id': '359', 'home_away': 'away', 'goals_for': 1},
        {'event_id': '269868', 'opponent_id': '359', 'home_away': 'away', 'goals_for': 0},
        {'event_id': '270000', 'opponent_id': '359', 'home_away': 'home', 'goals_for': 2},
    ]
    kept = sorted(espn.dedupe_league_matches(rows), key=lambda r: r['event_id'])
    assert [r['event_id'] for r in kept] == ['269868', '270000']


def test_running_totals_skip_unplayed():
    matches = [espn.parse_event(e) for e in [
        espn_event('1', '2026-08-15T14:00Z', True, 2, 0),
        espn_event('2', '2026-08-22T14:00Z', False, 1, 1, opp_id='2'),
        espn_event('3', '2026-08-29T14:00Z', True, 0, 0, opp_id='3', completed=False),
    ]]
    df = matches_mod.add_running_totals(matches)
    assert df['match_no'].tolist()[:2] == [1, 2] and pd.isna(df['match_no'].iloc[2])
    assert df['cum_points'].tolist()[:2] == [3, 4]
    assert df['cum_goal_difference'].iloc[1] == 2
    schedule = matches_mod.build_schedule(df)
    assert schedule['placement'].tolist() == ['last', 'last', 'next']
    assert schedule['score'].tolist()[:2] == ['2-0', '1-1']


def test_table_by_gameweek_orders_by_points_then_goal_difference():
    teams = {i: {'name': n, 'short_name': n[:3].upper()} for i, n in [(1, 'Alpha'), (2, 'Bravo'), (3, 'Charlie'), (4, 'Delta')]}
    fixtures = [
        {'event': 1, 'finished': True, 'team_h': 1, 'team_a': 2, 'team_h_score': 3, 'team_a_score': 0},
        {'event': 1, 'finished': True, 'team_h': 3, 'team_a': 4, 'team_h_score': 1, 'team_a_score': 0},
        {'event': 2, 'finished': True, 'team_h': 2, 'team_a': 3, 'team_h_score': 2, 'team_a_score': 2},
        {'event': 2, 'finished': False, 'team_h': 4, 'team_a': 1, 'team_h_score': None, 'team_a_score': None},
    ]
    table = table_progression.table_by_gameweek(table_progression.results_from_fixtures(fixtures), teams)
    gw1 = table[table['gameweek'] == 1].set_index('team')
    assert gw1.loc['Alpha', 'position'] == 1 and gw1.loc['Charlie', 'position'] == 2
    gw2 = table[table['gameweek'] == 2].set_index('team')
    assert gw2.loc['Charlie', 'points'] == 4 and gw2.loc['Charlie', 'position'] == 1
    assert gw2.loc['Alpha', 'played'] == 1  # postponed/unfinished game not counted


def test_display_name_prefers_everyday_names():
    assert player_stats.display_name({'known_name': 'Kevin', 'first_name': 'Kevin',
                                      'second_name': 'Santos Lopes de Macedo', 'web_name': 'Kevin'}) == 'Kevin'
    assert player_stats.display_name({'known_name': '', 'first_name': 'Jorge',
                                      'second_name': 'Cuenca Barreno', 'web_name': 'J.Cuenca'}) == 'Jorge Cuenca'
    assert player_stats.display_name({'known_name': '', 'first_name': 'Gonzalo',
                                      'second_name': 'García', 'web_name': 'Gonzalo'}) == 'Gonzalo García'


def table_rows(points_by_team, fulham_pos):
    rows = []
    for pos, (team, pts) in enumerate(points_by_team, start=1):
        rows.append({'position': pos, 'team': team, 'points': pts, 'is_team': pos == fulham_pos})
    return rows


def test_safety_context_inside_and_outside_drop_zone():
    teams = [(f"T{i}", 40 - i * 2) for i in range(1, 21)]  # 38, 36, ..., 0
    in_drop = table_rows(teams, 19)
    assert toplines.safety_context(in_drop, in_drop[18]) == ('Points from safety', '4')
    safe = table_rows(teams, 15)
    assert toplines.safety_context(safe, safe[14]) == ('Points above the drop zone', '6')


def test_describe_match():
    m = {'result': 'L', 'goals_for': 2, 'goals_against': 3, 'opponent': 'Chelsea',
         'home_away': 'home', 'venue': 'Craven Cottage'}
    assert toplines.describe_match(m) == 'a 3-2 loss to Chelsea at Craven Cottage'


def test_matchday_stage_progression():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(config.TEAM_TIMEZONE)
    match = {'event_id': '9', 'kickoff_utc': '2026-10-10T14:00Z', 'completed': False, 'result': None}
    at = lambda h, m=0: datetime(2026, 10, 10, h, m, tzinfo=tz)
    assert matchday.next_stage(match, at(7), set()) is None          # too early
    assert matchday.next_stage(match, at(9), set()) == 'preview'
    assert matchday.next_stage(match, at(14), {'preview_9'}) == 'lineup'
    assert matchday.next_stage(match, at(11), {'preview_9'}) is None  # before lineup window
    done = dict(match, completed=True, result='W')
    assert matchday.next_stage(done, at(17), {'preview_9', 'lineup_9'}) == 'result'
    assert matchday.next_stage(done, at(18), {'result_9'}) is None


def test_fit_post_respects_limit_and_keeps_link():
    text = "Header\n\n" + "\n".join(f"• line {i} " + "x" * 40 for i in range(10)) + "\n\nMore: https://example.com"
    fitted = common.fit_post(text)
    assert len(fitted) <= common.BLUESKY_MAX_CHARS
    assert fitted.endswith("More: https://example.com")


def test_rich_text_links_urls():
    builder = common.build_rich_text("Read https://example.com/a now")
    assert builder.build_text() == "Read https://example.com/a now"
    facets = builder.build_facets()
    assert len(facets) == 1 and facets[0].features[0].uri == "https://example.com/a"
