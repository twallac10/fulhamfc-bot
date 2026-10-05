#!/usr/bin/env python
# coding: utf-8

"""
Fulham squad and availability
Combines ESPN's squad list (shirt numbers, positions, ages, nationalities) with
Fantasy Premier League availability flags and injury/suspension news. Also
writes an availability log the Bluesky availability bot reads.
"""

import logging
import sys

from scripts import config
from scripts.common import ESPN_SITE_API, get_json, normalize_name, save_outputs, today_str
from scripts import fpl

GROUP_ORDER = ['Goalkeepers', 'Defenders', 'Midfielders', 'Forwards']
ESPN_GROUPS = {'G': 'Goalkeepers', 'D': 'Defenders', 'M': 'Midfielders', 'F': 'Forwards'}


def fpl_lookup(data, team):
    """Index the club's FPL players by full name and by surname (when unique)."""
    players = [p for p in data['elements'] if p['team'] == team]
    by_full, by_last = {}, {}
    for p in players:
        by_full[normalize_name(f"{p['first_name']} {p['second_name']}")] = p
        by_full[normalize_name(p['web_name'])] = p
        by_last.setdefault(normalize_name(p['second_name']).split(' ')[-1], []).append(p)
    return by_full, {k: v[0] for k, v in by_last.items() if len(v) == 1}


def match_fpl(athlete, by_full, by_last):
    name = normalize_name(athlete.get('displayName'))
    if name in by_full:
        return by_full[name]
    last = normalize_name(athlete.get('lastName') or name.split(' ')[-1]).split(' ')[-1]
    return by_last.get(last)


def build_squad(roster, data, team):
    by_full, by_last = fpl_lookup(data, team)
    squad = []
    for athlete in roster.get('athletes', []):
        p = match_fpl(athlete, by_full, by_last)
        pos_abbr = (athlete.get('position') or {}).get('abbreviation', '')[:1]
        group = fpl.POSITION_GROUPS.get(p['element_type']) if p else ESPN_GROUPS.get(pos_abbr, 'Squad')
        height_in, weight_lb = athlete.get('height'), athlete.get('weight')
        status = p['status'] if p else 'a'
        squad.append({
            'name': athlete.get('displayName'),
            'jersey': athlete.get('jersey') or (p.get('squad_number') if p else None),
            'position': (athlete.get('position') or {}).get('displayName'),
            'position_group': group,
            'age': athlete.get('age'),
            'nationality': athlete.get('citizenship'),
            'height_cm': round(height_in * 2.54) if height_in else None,
            'weight_kg': round(weight_lb * 0.4536) if weight_lb else None,
            'fpl_id': p['id'] if p else None,
            'status': status,
            'status_label': fpl.STATUS_LABELS.get(status, 'Available'),
            'is_available': status == 'a',
            'news': (p.get('news') or None) if p else None,
            'news_added': p.get('news_added') if p else None,
            'chance_of_playing': p.get('chance_of_playing_next_round') if p else None,
            'minutes': p.get('minutes', 0) if p else 0,
        })
    squad.sort(key=lambda s: (GROUP_ORDER.index(s['position_group']) if s['position_group'] in GROUP_ORDER else 9,
                              int(s['jersey']) if str(s['jersey'] or '').isdigit() else 999))
    return squad


def availability(squad):
    """Players with an injury, suspension or other availability note."""
    return [
        {
            'name': s['name'],
            'fpl_id': s['fpl_id'],
            'status': s['status'],
            'status_label': s['status_label'],
            'news': s['news'],
            'news_added': s['news_added'],
            'chance_of_playing': s['chance_of_playing'],
            'checked': today_str(),
        }
        for s in squad if s['news'] or s['status'] != 'a'
    ]


def main():
    roster = get_json(f"{ESPN_SITE_API}/teams/{config.ESPN_TEAM_ID}/roster")
    data = fpl.bootstrap()
    squad = build_squad(roster, data, fpl.team_id(data))
    if not squad:
        logging.error("ESPN returned an empty squad.")
        sys.exit(1)
    unmatched = [s['name'] for s in squad if s['fpl_id'] is None]
    if unmatched:
        logging.info(f"No FPL match (availability unknown) for: {', '.join(unmatched)}")
    save_outputs(squad, "fulham_squad_current", "squad")
    save_outputs(availability(squad), "fulham_availability", "squad")


if __name__ == "__main__":
    main()
