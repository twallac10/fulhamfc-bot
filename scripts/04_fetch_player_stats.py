#!/usr/bin/env python
# coding: utf-8

"""
Fulham player and team statistics
Pulls season-to-date player stats (goals, assists, expected goals, minutes,
cards, saves...) from the Fantasy Premier League API, then aggregates every
club's players to rank Fulham's attacking and disciplinary numbers across the
league.
"""

import logging

import pandas as pd

from scripts import config
from scripts.common import save_outputs
from scripts import fpl

NUMERIC = ['minutes', 'starts', 'goals_scored', 'assists', 'expected_goals', 'expected_assists',
           'expected_goal_involvements', 'clean_sheets', 'goals_conceded', 'expected_goals_conceded',
           'saves', 'penalties_saved', 'yellow_cards', 'red_cards', 'own_goals', 'tackles',
           'clearances_blocks_interceptions', 'recoveries', 'defensive_contribution', 'bonus',
           'total_points']


def display_name(p):
    """Everyday name: FPL's known_name, else first name + shirt surname
    ('Jorge Cuenca', not the registered 'Jorge Cuenca Barreno')."""
    if p.get('known_name'):
        return p['known_name']
    surname = str(p['web_name']).split('.')[-1].strip()
    if not surname or surname == p['first_name']:
        surname = p['second_name']
    return f"{p['first_name']} {surname}".strip()


def players_frame(data):
    teams = {t['id']: t['name'] for t in data['teams']}
    df = pd.DataFrame(data['elements'])
    for col in NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    df['team'] = df['team'].map(teams)
    df['name'] = df.apply(display_name, axis=1)
    df['position'] = df['element_type'].map(fpl.POSITIONS)
    df['position_group'] = df['element_type'].map(fpl.POSITION_GROUPS)
    df['status_label'] = df['status'].map(fpl.STATUS_LABELS).fillna('Available')
    return df


def team_player_table(df, team_name=config.FPL_TEAM_NAME):
    """Fulham players, with per-90 rates for anyone who has played."""
    ours = df[df['team'] == team_name].copy()
    nineties = ours['minutes'] / 90
    for stat in ['goals_scored', 'assists', 'expected_goals', 'expected_assists', 'expected_goal_involvements']:
        ours[f'{stat}_per_90'] = (ours[stat] / nineties).where(ours['minutes'] >= 90).round(2)
    ours['goals_minus_xg'] = (ours['goals_scored'] - ours['expected_goals']).round(2)
    cols = ['id', 'name', 'web_name', 'position', 'position_group', 'squad_number', 'status',
            'status_label', 'news', 'chance_of_playing_next_round'] + NUMERIC + \
        ['goals_scored_per_90', 'assists_per_90', 'expected_goals_per_90', 'expected_assists_per_90',
         'expected_goal_involvements_per_90', 'goals_minus_xg']
    ours = ours[[c for c in cols if c in ours.columns]]
    return ours.sort_values(['minutes', 'goals_scored'], ascending=False).reset_index(drop=True)


# (column, label, higher_is_better)
TEAM_STATS = [
    ('goals_scored', 'Goals (excl. own goals)', True),
    ('expected_goals', 'Expected goals (xG)', True),
    ('assists', 'Assists', True),
    ('expected_assists', 'Expected assists (xA)', True),
    ('saves', 'Saves', True),
    ('yellow_cards', 'Yellow cards', False),
    ('red_cards', 'Red cards', False),
]


def team_ranks(df, team_name=config.FPL_TEAM_NAME):
    """Sum player stats by club and rank Fulham across the league (1 = best)."""
    totals = df.groupby('team')[[c for c, _, _ in TEAM_STATS]].sum()
    out = []
    for col, label, higher_is_better in TEAM_STATS:
        ranks = totals[col].rank(ascending=not higher_is_better, method='min')
        out.append({
            'stat': col,
            'label': label,
            'value': round(float(totals.loc[team_name, col]), 2),
            'rank': int(ranks.loc[team_name]),
            'league_avg': round(float(totals[col].mean()), 2),
            'teams': int(len(totals)),
        })
    return out


def main():
    data = fpl.bootstrap()
    df = players_frame(data)
    players = team_player_table(df)
    if players.empty:
        logging.error(f"No {config.FPL_TEAM_NAME} players found in FPL data.")
        raise SystemExit(1)
    save_outputs(players, "fulham_players_current", "players")
    save_outputs(team_ranks(df), "fulham_team_stat_ranks", "players")


if __name__ == "__main__":
    main()
