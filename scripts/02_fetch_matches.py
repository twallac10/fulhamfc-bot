#!/usr/bin/env python
# coding: utf-8

"""
Fulham results and fixtures
Fetches every league match for the current season from ESPN, adds running
totals (points, goal difference) and builds a last-five/next-five schedule.
"""

import logging
import sys

import pandas as pd

from scripts import config
from scripts.common import save_outputs
from scripts.espn import fetch_team_matches


def add_running_totals(matches):
    """Number played matches and add cumulative points/goals. Expects oldest first."""
    df = pd.DataFrame(matches)
    played = df['completed'] & df['result'].notna()
    df['match_no'] = None
    df.loc[played, 'match_no'] = range(1, int(played.sum()) + 1)
    df['cum_points'] = df['points'].where(played).cumsum()
    df['cum_goals_for'] = df['goals_for'].where(played).cumsum()
    df['cum_goals_against'] = df['goals_against'].where(played).cumsum()
    df['cum_goal_difference'] = df['cum_goals_for'] - df['cum_goals_against']
    int_cols = ['match_no', 'goals_for', 'goals_against', 'points',
                'cum_points', 'cum_goals_for', 'cum_goals_against', 'cum_goal_difference']
    for col in int_cols:
        df[col] = pd.to_numeric(df[col]).where(played).astype('Int64')
    df['season'] = config.season_label()
    return df


def build_schedule(df, n=5):
    """Last n results and next n fixtures, mirroring the dashboard's schedule tables."""
    played = df[df['match_no'].notna()].tail(n).copy()
    upcoming = df[df['match_no'].isna() & ~df['status'].isin(['STATUS_POSTPONED', 'STATUS_CANCELED'])].head(n).copy()
    played['placement'] = 'last'
    upcoming['placement'] = 'next'
    played['score'] = played['goals_for'].astype(int).astype(str) + '-' + played['goals_against'].astype(int).astype(str)
    upcoming['score'] = None
    upcoming.loc[~upcoming['time_valid'], 'kickoff_local'] = 'TBC'
    cols = ['placement', 'event_id', 'date', 'kickoff_local', 'home_away', 'opponent', 'opponent_abbr',
            'venue', 'result', 'score']
    return pd.concat([played[cols], upcoming[cols]], ignore_index=True)


def main():
    matches = fetch_team_matches(config.SEASON_START_YEAR)
    if not matches:
        logging.warning(f"No {config.season_label()} matches published yet. Exiting without saving.")
        sys.exit(0)
    df = add_running_totals(matches)
    save_outputs(df, "fulham_matches_current", "matches")
    save_outputs(build_schedule(df), "fulham_schedule", "matches")


if __name__ == "__main__":
    main()
