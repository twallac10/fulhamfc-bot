"""
Thin wrappers around ESPN's public soccer API, shared by several scripts.
"""

from scripts import config
from scripts.common import ESPN_SITE_API, ESPN_STANDINGS_API, get_json, to_local


def _score(competitor):
    score = competitor.get('score')
    if isinstance(score, dict):
        score = score.get('value', score.get('displayValue'))
    if score in (None, ''):
        return None
    return int(float(score))


def parse_event(event, team_id=config.ESPN_TEAM_ID):
    """Flatten an ESPN schedule event into one row from the team's point of view."""
    competition = event['competitions'][0]
    competitors = competition['competitors']
    us = next(c for c in competitors if str(c['id']) == str(team_id))
    them = next(c for c in competitors if str(c['id']) != str(team_id))
    status = competition.get('status', {}).get('type', {})
    completed = bool(status.get('completed'))
    kickoff = to_local(event['date'])

    goals_for = _score(us) if completed else None
    goals_against = _score(them) if completed else None
    result = None
    if completed and goals_for is not None and goals_against is not None:
        result = 'W' if goals_for > goals_against else 'L' if goals_for < goals_against else 'D'

    return {
        'event_id': str(event['id']),
        'kickoff_utc': event['date'],
        'date': kickoff.strftime('%Y-%m-%d'),
        'kickoff_local': kickoff.strftime('%H:%M'),
        'time_valid': bool(event.get('timeValid', True)),
        'home_away': us.get('homeAway'),
        'opponent': them['team']['displayName'],
        'opponent_short': them['team'].get('shortDisplayName', them['team']['displayName']),
        'opponent_abbr': them['team'].get('abbreviation'),
        'opponent_id': str(them['id']),
        'venue': competition.get('venue', {}).get('fullName'),
        'status': status.get('name'),
        'status_detail': status.get('shortDetail') or status.get('detail'),
        'completed': completed,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'result': result,
        'points': {'W': 3, 'D': 1, 'L': 0}.get(result),
    }


def fetch_team_matches(season, include_fixtures=True, team_id=config.ESPN_TEAM_ID):
    """All of a team's league matches for a season, played and upcoming, oldest first."""
    url = f"{ESPN_SITE_API}/teams/{team_id}/schedule"
    events = {}
    played = get_json(url, params={'season': season})
    for event in played.get('events', []):
        events[str(event['id'])] = event
    if include_fixtures:
        upcoming = get_json(url, params={'season': season, 'fixture': 'true'})
        for event in upcoming.get('events', []):
            events.setdefault(str(event['id']), event)
    rows = [parse_event(e, team_id) for e in events.values()]
    return sorted(dedupe_league_matches(rows), key=lambda r: r['kickoff_utc'])


def dedupe_league_matches(rows):
    """Each league pairing (opponent, home/away) happens once a season, but ESPN's
    feed for some older seasons (e.g. 2009-10) repeats most matches under newer
    event ids with unreliable scores. Keep the original (lowest id) event."""
    best = {}
    for row in rows:
        key = (row['opponent_id'], row['home_away'])
        if key not in best or int(row['event_id']) < int(best[key]['event_id']):
            best[key] = row
    return list(best.values())


def fetch_standings(season):
    """League table for a season, ordered by position."""
    data = get_json(ESPN_STANDINGS_API, params={'season': season})
    if not data.get('children'):
        raise LookupError(f"ESPN has no {config.ESPN_LEAGUE} standings for season {season}")
    standings = data['children'][0]['standings']
    rows = []
    for entry in standings['entries']:
        stats = {s['name']: s for s in entry['stats']}

        def num(name):
            value = stats.get(name, {}).get('value')
            return int(value) if value is not None else None

        note = entry.get('note') or {}
        rows.append({
            'position': num('rank'),
            'team_id': str(entry['team']['id']),
            'team': entry['team']['displayName'],
            'team_short': entry['team'].get('shortDisplayName', entry['team']['displayName']),
            'abbr': entry['team'].get('abbreviation'),
            'played': num('gamesPlayed'),
            'won': num('wins'),
            'drawn': num('ties'),
            'lost': num('losses'),
            'goals_for': num('pointsFor'),
            'goals_against': num('pointsAgainst'),
            'goal_difference': num('pointDifferential'),
            'points': num('points'),
            'deductions': stats.get('deductions', {}).get('displayValue') or None,
            'zone': note.get('description'),
            'zone_color': (note.get('color') or '').replace('##', '#') or None,
        })
    rows.sort(key=lambda r: (r['position'] is None, r['position']))
    return {
        'season_label': standings.get('seasonDisplayName'),
        'rows': rows,
    }


def fetch_summary(event_id):
    return get_json(f"{ESPN_SITE_API}/summary", params={'event': event_id})


LINE_BY_POSITION = {
    'G': 0,
    'SW': 1, 'RB': 1, 'CD-R': 1, 'CD': 1, 'CD-L': 1, 'LB': 1,
    'DM-R': 2, 'DM': 2, 'DM-L': 2,
    'RWB': 3, 'RM': 3, 'CM-R': 3, 'CM': 3, 'CM-L': 3, 'LM': 3, 'LWB': 3, 'M': 3,
    'AM-R': 4, 'AM': 4, 'AM-L': 4, 'RW': 4, 'LW': 4,
    'F': 5, 'CF-R': 5, 'CF': 5, 'CF-L': 5, 'ST': 5,
}


def _pitch_order(abbr):
    """Sort key: goalkeeper to forwards, right side to left side within a line."""
    abbr = (abbr or '').upper()
    if abbr.endswith('-R'):
        side = 1
    elif abbr.endswith('-L'):
        side = 3
    elif abbr.startswith('R'):
        side = 0
    elif abbr.startswith('L'):
        side = 4
    else:
        side = 2
    return LINE_BY_POSITION.get(abbr, 3), side


def starting_lineup(summary, team_id=config.ESPN_TEAM_ID):
    """Return (formation, [[line of surnames], ...]) ordered keeper to attack,
    or (None, []) if the XI hasn't been announced."""
    for roster in summary.get('rosters', []):
        if str(roster.get('team', {}).get('id')) != str(team_id):
            continue
        starters = [p for p in roster.get('roster', []) if p.get('starter')]
        if not starters:
            return None, []
        starters.sort(key=lambda p: _pitch_order(p.get('position', {}).get('abbreviation')))
        lines = {}
        for p in starters:
            line = _pitch_order(p.get('position', {}).get('abbreviation'))[0]
            lines.setdefault(line, []).append(p['athlete'].get('lastName') or p['athlete']['displayName'])
        return roster.get('formation'), [lines[k] for k in sorted(lines)]
    return None, []


def goal_events(summary):
    """Goals as [{'team_id', 'team', 'scorer', 'minute', 'own_goal', 'penalty'}]."""
    goals = []
    for event in summary.get('keyEvents', []):
        type_text = (event.get('type', {}).get('type') or '').lower()
        is_goal = event.get('scoringPlay') or type_text.startswith('goal') or 'penalty---scored' in type_text \
            or 'own-goal' in type_text
        if not is_goal or 'disallowed' in type_text or 'missed' in type_text:
            continue
        participants = event.get('participants') or []
        scorer = participants[0]['athlete']['displayName'] if participants else None
        goals.append({
            'team_id': str(event.get('team', {}).get('id')),
            'team': event.get('team', {}).get('displayName'),
            'scorer': scorer,
            'minute': event.get('clock', {}).get('displayValue'),
            'own_goal': 'own' in type_text,
            'penalty': 'penalty' in type_text,
        })
    return goals
