#!/usr/bin/env python
# coding: utf-8

"""
Availability updates for Bluesky
The football counterpart of the Brewers bot's transactions posts: whenever a
Fulham player's injury/suspension note changes (per the Fantasy Premier League
availability feed saved by 05_fetch_squad.py), post the update once.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from scripts import config
from scripts.common import (add_posted_id, get_posted_ids, load_output, now_local, post_to_bluesky,
                            read_s3_text, s3_key)

STATE = "posted_availability"
MAX_AGE_DAYS = 7
EMOJI = {'i': '🩹', 'd': '❓', 's': '🟥', 'u': '🚫', 'n': '🚫', 'a': '✅'}


def update_id(item):
    return f"{item['fpl_id']}_{item['status']}_{item['news'] or ''}"[:200]


def format_update(item):
    chance = item.get('chance_of_playing')
    chance_text = f" ({chance}% chance of playing)" if chance not in (None, 0, 100) else ""
    news = item['news'] or item['status_label']
    return f"{EMOJI.get(item['status'], '📋')} {config.TEAM_NAME} availability: {item['name']}\n\n{news}{chance_text}"


def recent(item, now_utc):
    if not item.get('news_added'):
        return False
    added = datetime.fromisoformat(item['news_added'].replace('Z', '+00:00'))
    return now_utc - added <= timedelta(days=MAX_AGE_DAYS)


def load_availability():
    text = read_s3_text(s3_key("squad", "fulham_availability.json"))
    return json.loads(text) if text else load_output("fulham_availability", "squad")


def main():
    parser = argparse.ArgumentParser(description=f"Post {config.TEAM_NAME} availability updates to Bluesky.")
    parser.add_argument("--post", action="store_true", help="Publish to Bluesky (otherwise dry run).")
    parser.add_argument("--force", action="store_true", help="Ignore the posting-hours window.")
    args = parser.parse_args()

    hour = now_local().hour
    if args.post and not args.force and not 8 <= hour <= 22:
        logging.info(f"Outside posting hours (hour: {hour}). Skipping.")
        return

    items = load_availability() or []
    posted = set(get_posted_ids(STATE))
    now_utc = datetime.now(timezone.utc)
    new = [i for i in items if i.get('fpl_id') and i.get('news') and recent(i, now_utc)
           and update_id(i) not in posted]
    if not new:
        logging.info("No new availability updates.")
        return

    for item in sorted(new, key=lambda i: i['news_added']):
        text = format_update(item)
        print(f"--- {update_id(item)} ---\n{text}\n")
        if args.post and post_to_bluesky(text):
            add_posted_id(STATE, update_id(item))
            time.sleep(2)
    if not args.post:
        logging.info("Dry run: --post flag not provided. Not posting to Bluesky.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)
