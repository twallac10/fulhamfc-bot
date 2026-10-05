#!/usr/bin/env python
# coding: utf-8

"""
Dashboard summary statistics
Combines this run's league table, results, player stats and history into the
headline sentence and stat cards shown at the top of the dashboard (and used
by the Bluesky report bot).
"""

import logging
import sys
from datetime import datetime

import pandas as pd

from scripts import config
from scripts.common import load_output, ordinal, save_outputs

RELEGATION_PLACES = 3


def pts(n):
    return f"{n} point{'s' if n != 1 else ''}"


def nice_date(iso_date, with_weekday=False):
    d = datetime.strptime(iso_date, '%Y-%m-%d')
    return d.strftime('%A, %B %-d' if with_weekday else '%B %-d')


def describe_match(m):
    """'a 3-2 loss to Chelsea at Craven Cottage'."""
    word = {'W': 'win', 'D': 'draw', 'L': 'loss'}[m['result']]
    joiner = {'W': 'over', 'D': 'with', 'L': 'to'}[m['result']]
    score = f"{max(m['goals_for'], m['goals_against'])}-{min(m['goals_for'], m['goals_against'])}"
    where = f"at {m['venue']}" if m['home_away'] == 'home' and m.get('venue') else "away"
    return f"a {score} {word} {joiner} {m['opponent']} {where}"


def safety_context(table, ours):
    """Gap to the relegation zone, from Fulham's point of view."""
    n = len(table)
    safe_line = table[n - RELEGATION_PLACES - 1]   # last place above the drop
    first_drop = table[n - RELEGATION_PLACES]      # first relegation place
    if ours['position'] > n - RELEGATION_PLACES:
        gap = safe_line['points'] - ours['points']
        return 'Points from safety', f"{gap}"
    gap = ours['points'] - first_drop['points']
    return 'Points above the drop zone', f"{gap}"


def build_summary(table, matches, players, team_ranks, history):
    ours = next(r for r in table if r['is_team'])
    played = [m for m in matches if m.get('match_no')]
    upcoming = [m for m in matches if not m.get('match_no')
                and m['status'] not in ('STATUS_POSTPONED', 'STATUS_CANCELED')]
    stats = []

    def add(stat, label, value, context_label=None, context_value=None, category=None):
        stats.append({'stat': stat, 'stat_label': label, 'value': value,
                      'context_value_label': context_label, 'context_value': context_value,
                      'category': category})

    position_text = f"{ordinal(ours['position'])} in the {config.LEAGUE_NAME}"
    if played:
        last = played[-1]
        sentence = (f"{config.TEAM_NAME} are <span class='highlight'>{position_text}</span> with "
                    f"{pts(ours['points'])} from {ours['played']} matches after "
                    f"{describe_match(last)} ({nice_date(last['date'])}).")
        add('last_match_result', 'Last result', {'W': 'win', 'D': 'draw', 'L': 'loss'}[last['result']])
        add('last_match_date', 'Last match date', last['date'])
        add('last_match_event_id', 'Last match id', last['event_id'])
    else:
        sentence = f"The {config.season_label()} {config.LEAGUE_NAME} season hasn't kicked off for {config.TEAM_NAME} yet."
    if upcoming:
        nxt = upcoming[0]
        venue = 'vs' if nxt['home_away'] == 'home' else 'at'
        sentence += f" Next: {venue} {nxt['opponent']} on {nice_date(nxt['date'], with_weekday=True)}."
        add('next_match', 'Next match', f"{venue} {nxt['opponent']}", 'Kickoff',
            f"{nice_date(nxt['date'])}, {nxt['kickoff_local'] if nxt['time_valid'] else 'TBC'}")
    add('summary', 'Summary', sentence)

    # --- Standings cards ---
    zone = f"{ours['zone']} place" if ours.get('zone') else 'Mid-table'
    add('position', 'League position', ordinal(ours['position']), 'Zone', zone, 'standings')
    safety_label, safety_value = safety_context(table, ours)
    add('points', 'Points', ours['points'], safety_label, safety_value, 'standings')
    add('record', 'Won-drawn-lost', f"{ours['won']}-{ours['drawn']}-{ours['lost']}",
        'Goal difference', f"{ours['goal_difference']:+d}", 'standings')

    if played:
        form = played[-5:]
        add('form', 'Form (last 5)', ''.join(m['result'] for m in form),
            'Points from last 5', sum(m['points'] for m in form), 'standings')
        ppg = ours['points'] / ours['played']
        last_season = next((s for s in reversed(history or []) if s.get('played')
                            and s['start_year'] == config.SEASON_START_YEAR - 1), None)
        add('projected_points', 'Projected points', round(ppg * config.LEAGUE_MATCHES),
            f"Last season ({last_season['season']})" if last_season else 'Points per match',
            f"{last_season['points']} pts" if last_season else f"{ppg:.2f}", 'standings')

        # Same stage of previous Premier League seasons
        n = len(played)
        same_stage = [m for m in (load_output("fulham_pl_history_matches", "history") or [])
                      if m['match_no'] == n]
        if same_stage:
            best = max(same_stage, key=lambda m: m['cum_points'])
            better = sum(1 for m in same_stage if m['cum_points'] > ours['points'])
            add('same_stage', f"Points after {n} matches", ours['points'],
                f"Rank among {len(same_stage) + 1} PL seasons",
                f"{ordinal(better + 1)} (best: {best['cum_points']} in {best['season']})", 'standings')

    # --- Attack / defence cards ---
    t = pd.DataFrame(table)
    gf_rank = int(t['goals_for'].rank(ascending=False, method='min')[t['is_team']].iloc[0])
    ga_rank = int(t['goals_against'].rank(ascending=True, method='min')[t['is_team']].iloc[0])
    add('goals_for', 'Goals scored', ours['goals_for'], 'League rank', ordinal(gf_rank), 'attack')
    add('goals_against', 'Goals conceded', ours['goals_against'], 'League rank (fewest)', ordinal(ga_rank), 'defence')
    ranks = {r['stat']: r for r in team_ranks or []}
    if 'expected_goals' in ranks:
        xg = ranks['expected_goals']
        add('expected_goals', 'Expected goals (xG)', f"{xg['value']:.1f}", 'League rank', ordinal(xg['rank']), 'attack')
    clean_sheets = sum(1 for m in played if m['goals_against'] == 0)
    add('clean_sheets', 'Clean sheets', clean_sheets, 'Matches played', len(played), 'defence')
    if 'yellow_cards' in ranks:
        yc, rc = ranks['yellow_cards'], ranks.get('red_cards', {'value': 0})
        add('cards', 'Yellow / red cards', f"{int(yc['value'])} / {int(rc['value'])}",
            'League rank (fewest yellows)', ordinal(yc['rank']), 'defence')
    if players:
        top = max(players, key=lambda p: (p['goals_scored'], p['assists'], -p['minutes']))
        if top['goals_scored'] > 0:
            add('top_scorer', 'Top scorer', top['name'], 'Goals', int(top['goals_scored']), 'attack')
        creator = max(players, key=lambda p: (p['assists'], p['expected_assists']))
        if creator['assists'] > 0:
            add('top_assister', 'Most assists', creator['name'], 'Assists', int(creator['assists']), 'attack')
    return stats


def main():
    table = load_output("league_table", "standings")
    matches = load_output("fulham_matches_current", "matches")
    if not table or matches is None:
        logging.error("League table or matches missing. Run scripts 01 and 02 first.")
        sys.exit(1)
    stats = build_summary(
        table, matches,
        load_output("fulham_players_current", "players"),
        load_output("fulham_team_stat_ranks", "players"),
        load_output("fulham_pl_seasons", "history"),
    )
    save_outputs(stats, "season_summary_latest", "standings")
    logging.info(next(s['value'] for s in stats if s['stat'] == 'summary'))


if __name__ == "__main__":
    main()
