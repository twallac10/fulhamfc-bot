#!/usr/bin/env python
# coding: utf-8

"""
Weekly stat reports for Bluesky
Football has one or two matches a week, so instead of daily summaries the bot
posts a rotating set of reports from the dashboard's summary data:

    Monday     table    - league position, points, gap to the drop, form
    Wednesday  attack   - goals, xG, top scorer and creator
    Thursday   defence  - goals conceded, clean sheets, cards

Each type posts at most once a day. Match results are posted by
10_post_matchday.py.
"""

import argparse
import json
import logging
import sys

from scripts import config
from scripts.common import (get_last_post_date, load_output, now_local, post_to_bluesky, read_s3_text,
                            s3_key, set_last_post_date, today_str)

SCHEDULE = {0: 'table', 2: 'attack', 3: 'defence'}  # weekday -> report


def load_summary():
    text = read_s3_text(s3_key("standings", "season_summary_latest.json"))
    if text:
        return json.loads(text)
    return load_output("season_summary_latest", "standings")


def stat_line(stats, key, fmt="{label}: {value} ({context})"):
    s = stats.get(key)
    if not s:
        return None
    return fmt.format(label=s['stat_label'], value=s['value'], context=s['context_value'],
                      context_label=s['context_value_label'])


def format_report(report_type, stats):
    header = {
        'table': f"📊 {config.TEAM_NAME} {config.LEAGUE_NAME} check-in",
        'attack': f"⚽ {config.TEAM_NAME} attack report",
        'defence': f"🧤 {config.TEAM_NAME} defence report",
    }[report_type]
    if report_type == 'table':
        lines = [
            stat_line(stats, 'position', "• {value} ({context})"),
            stat_line(stats, 'points', "• {value} pts — {context_label}: {context}"),
            stat_line(stats, 'record', "• W-D-L: {value}, GD {context}"),
            stat_line(stats, 'form', "• Form: {value}"),
            stat_line(stats, 'next_match', "• Next: {value} ({context})"),
        ]
    elif report_type == 'attack':
        lines = [
            stat_line(stats, 'goals_for', "• Goals: {value} ({context} in PL)"),
            stat_line(stats, 'expected_goals', "• xG: {value} ({context} in PL)"),
            stat_line(stats, 'top_scorer', "• Top scorer: {value} ({context})"),
            stat_line(stats, 'top_assister', "• Most assists: {value} ({context})"),
        ]
    else:
        lines = [
            stat_line(stats, 'goals_against', "• Conceded: {value} ({context} fewest in PL)"),
            stat_line(stats, 'clean_sheets', "• Clean sheets: {value} in {context} matches"),
            stat_line(stats, 'cards', "• Cards (Y/R): {value}"),
        ]
    body = "\n".join(line for line in lines if line)
    if not body:
        return None
    return f"{header}\n\n{body}\n\nMore: {config.SITE_URL}"


def main():
    parser = argparse.ArgumentParser(description=f"Post weekly {config.TEAM_NAME} stat reports to Bluesky.")
    parser.add_argument("--type", default="auto", choices=['auto', 'table', 'attack', 'defence'],
                        help="Report to post. 'auto' picks by weekday.")
    parser.add_argument("--dry-run", action="store_true", help="Print the post without publishing it.")
    args = parser.parse_args()

    report_type = SCHEDULE.get(now_local().weekday()) if args.type == 'auto' else args.type
    if not report_type:
        logging.info("No report scheduled today.")
        return
    if not args.dry_run and get_last_post_date(report_type) == today_str():
        logging.info(f"'{report_type}' report already posted today. Skipping.")
        return

    summary = load_summary()
    if not summary:
        logging.error("No season summary available.")
        sys.exit(1)
    stats = {s['stat']: s for s in summary}
    if 'position' not in stats or not stats.get('last_match_date'):
        logging.info("Season hasn't started yet; nothing to report.")
        return

    post_text = format_report(report_type, stats)
    if not post_text:
        logging.error("Failed to generate post text.")
        return
    logging.info(f"Generated '{report_type}' post:\n{post_text}")
    if args.dry_run:
        return
    if post_to_bluesky(post_text):
        set_last_post_date(report_type)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)
