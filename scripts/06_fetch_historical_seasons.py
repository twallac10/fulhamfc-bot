#!/usr/bin/env python
# coding: utf-8

"""
Fulham in the Premier League, 2001-02 to last season
Builds match-by-match results (with running points totals) and final league
positions for every completed Premier League season Fulham played, so the
site can compare this season's points trajectory with the past.

Completed seasons never change, so results are cached on S3 and only missing
seasons are fetched. Pass --refresh to rebuild everything from ESPN.
Seasons outside the top flight (e.g. 2014-15 to 2017-18) are skipped.
"""

import argparse
import logging
import time

import pandas as pd

from scripts import config
from scripts.common import load_output, save_outputs
from scripts.espn import fetch_standings, fetch_team_matches


def season_matches(start_year):
    """Played league matches for one season, with running totals, or [] if Fulham weren't in it."""
    matches = [m for m in fetch_team_matches(start_year, include_fixtures=False) if m['result']]
    if len(matches) < config.LEAGUE_MATCHES:
        return []
    rows, points, gf, ga = [], 0, 0, 0
    for i, m in enumerate(matches[:config.LEAGUE_MATCHES], start=1):
        points += m['points']
        gf += m['goals_for']
        ga += m['goals_against']
        rows.append({
            'season': config.season_label(start_year),
            'start_year': start_year,
            'match_no': i,
            'date': m['date'],
            'home_away': m['home_away'],
            'opponent': m['opponent'],
            'goals_for': m['goals_for'],
            'goals_against': m['goals_against'],
            'result': m['result'],
            'cum_points': points,
            'cum_goal_difference': gf - ga,
        })
    return rows


def season_summary(start_year, matches):
    """Final record for a season. The official ESPN table wins where it is
    available; match-level data occasionally disagrees by a result or two."""
    results = pd.Series([m['result'] for m in matches])
    computed = {
        'played': len(matches),
        'won': int((results == 'W').sum()),
        'drawn': int((results == 'D').sum()),
        'lost': int((results == 'L').sum()),
        'goals_for': sum(m['goals_for'] for m in matches),
        'goals_against': sum(m['goals_against'] for m in matches),
        'points': matches[-1]['cum_points'],
    }
    try:
        standings = fetch_standings(start_year)['rows']
    except LookupError as e:
        logging.warning(f"{e}; using match-level totals")
        standings = []
    row = next((r for r in standings if r['team_id'] == config.ESPN_TEAM_ID), None)

    summary = {'season': config.season_label(start_year), 'start_year': start_year,
               'position': row['position'] if row else None, **computed,
               'zone': row['zone'] if row else None, 'matches_official_table': None}
    if row:
        official = {k: row[k] for k in computed}
        summary['matches_official_table'] = official == computed
        if official != computed:
            logging.warning(f"{summary['season']}: match data {computed} differs from official table "
                            f"{official}; using the official table for season totals")
            summary.update(official)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--refresh', action='store_true', help='Ignore the cache and refetch every season.')
    args = parser.parse_args()

    cached_matches = [] if args.refresh else (load_output("fulham_pl_history_matches", "history") or [])
    cached_seasons = [] if args.refresh else (load_output("fulham_pl_seasons", "history") or [])
    # Seasons already checked: in the PL (cached) or confirmed not (recorded with played == 0)
    known = {s['start_year'] for s in cached_seasons}

    all_matches = [m for m in cached_matches if m['start_year'] in known]
    seasons = list(cached_seasons)
    for year in range(config.HISTORY_START_YEAR, config.SEASON_START_YEAR):
        if year in known:
            continue
        logging.info(f"Fetching {config.season_label(year)}")
        matches = season_matches(year)
        if matches:
            all_matches.extend(matches)
            seasons.append(season_summary(year, matches))
        else:
            logging.info(f"{config.TEAM_NAME} not in the {config.LEAGUE_NAME} in {config.season_label(year)}")
            seasons.append({'season': config.season_label(year), 'start_year': year, 'played': 0})
        time.sleep(1)

    seasons.sort(key=lambda s: s['start_year'])
    all_matches.sort(key=lambda m: (m['start_year'], m['match_no']))
    save_outputs(all_matches, "fulham_pl_history_matches", "history")
    save_outputs(seasons, "fulham_pl_seasons", "history")
    logging.info(f"{sum(1 for s in seasons if s['played'])} Premier League seasons in history")


if __name__ == "__main__":
    main()
