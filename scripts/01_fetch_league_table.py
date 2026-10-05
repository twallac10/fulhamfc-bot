#!/usr/bin/env python
# coding: utf-8

"""
Premier League table
Fetches the current league table from ESPN and saves it for the site and S3.
"""

import logging
import sys

from scripts import config
from scripts.common import save_outputs
from scripts.espn import fetch_standings


def main():
    table = fetch_standings(config.SEASON_START_YEAR)
    rows = table['rows']
    if not rows:
        logging.error("ESPN returned an empty league table.")
        sys.exit(1)
    for row in rows:
        row['is_team'] = row['team_id'] == config.ESPN_TEAM_ID
    if not any(r['is_team'] for r in rows):
        logging.error(f"{config.TEAM_NAME} not found in the {config.season_label()} table.")
        sys.exit(1)
    save_outputs(rows, "league_table", "standings")


if __name__ == "__main__":
    main()
