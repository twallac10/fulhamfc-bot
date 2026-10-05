#!/usr/bin/env python
# coding: utf-8

"""
League position by matchweek
Rebuilds the Premier League table after every gameweek from the full fixture
list (Fantasy Premier League API), so the site can chart Fulham's position and
points against the rest of the league.
"""

import logging
import sys

import pandas as pd

from scripts import config
from scripts.common import save_outputs
from scripts import fpl


def results_from_fixtures(fixture_list):
    """One row per team per finished fixture."""
    rows = []
    for fx in fixture_list:
        if fx.get('event') is None or not (fx.get('finished') or fx.get('finished_provisional')):
            continue
        h, a = fx['team_h_score'], fx['team_a_score']
        if h is None or a is None:
            continue
        for team, gf, ga in ((fx['team_h'], h, a), (fx['team_a'], a, h)):
            rows.append({
                'gameweek': fx['event'],
                'team_id': team,
                'goals_for': gf,
                'goals_against': ga,
                'won': int(gf > ga),
                'drawn': int(gf == ga),
                'lost': int(gf < ga),
                'points': 3 if gf > ga else 1 if gf == ga else 0,
            })
    return pd.DataFrame(rows)


def table_by_gameweek(results, teams):
    """Cumulative table for every team after each completed gameweek.

    Ties are broken by goal difference, then goals scored, then name. (The
    Premier League's later tie-breakers rarely matter and aren't modelled.)
    """
    if results.empty:
        return pd.DataFrame()
    gameweeks = sorted(results['gameweek'].unique())
    team_ids = sorted(teams)
    totals = (results.groupby(['team_id', 'gameweek'])
              [['goals_for', 'goals_against', 'won', 'drawn', 'lost', 'points']].sum())
    full_index = pd.MultiIndex.from_product([team_ids, gameweeks], names=['team_id', 'gameweek'])
    played = results.groupby(['team_id', 'gameweek']).size().rename('played')
    totals = totals.join(played).reindex(full_index, fill_value=0)
    cum = totals.groupby(level='team_id').cumsum().reset_index()
    cum['goal_difference'] = cum['goals_for'] - cum['goals_against']
    cum['team'] = cum['team_id'].map(lambda t: teams[t]['name'])
    cum['abbr'] = cum['team_id'].map(lambda t: teams[t]['short_name'])
    cum = cum.sort_values(['gameweek', 'points', 'goal_difference', 'goals_for', 'team'],
                          ascending=[True, False, False, False, True])
    cum['position'] = cum.groupby('gameweek').cumcount() + 1
    return cum.reset_index(drop=True)


def main():
    data = fpl.bootstrap()
    teams = {t['id']: t for t in data['teams']}
    our_id = fpl.team_id(data)
    results = results_from_fixtures(fpl.fixtures())
    table = table_by_gameweek(results, teams)
    if table.empty:
        logging.warning("No finished fixtures yet. Exiting without saving.")
        sys.exit(0)
    table['is_team'] = table['team_id'] == our_id
    cols = ['gameweek', 'position', 'team', 'abbr', 'is_team', 'played', 'won', 'drawn', 'lost',
            'goals_for', 'goals_against', 'goal_difference', 'points']
    save_outputs(table[cols], "table_by_gameweek", "standings")
    logging.info(f"{config.TEAM_NAME} position by gameweek: "
                 f"{table[table['is_team']][['gameweek', 'position']].values.tolist()}")


if __name__ == "__main__":
    main()
