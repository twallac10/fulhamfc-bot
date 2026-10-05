#!/usr/bin/env python
# coding: utf-8

"""
Fulham news roundup
Fetches the latest Fulham headlines from ESPN, saves them for the dashboard
and (with --post) shares the newest story not posted before to Bluesky, at
most once a day.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from scripts import config
from scripts.common import (ESPN_SITE_API, add_posted_id, get_json, get_last_post_date, get_posted_ids,
                            now_local, post_to_bluesky, save_outputs, set_last_post_date, today_str)

POST_TYPE = "news"
MAX_AGE_HOURS = 48  # only share recent stories


def fetch_news(limit=10):
    data = get_json(f"{ESPN_SITE_API}/news", params={'team': config.ESPN_TEAM_ID, 'limit': limit})
    articles = []
    for a in data.get('articles', []):
        url = a.get('links', {}).get('web', {}).get('href')
        if not (a.get('headline') and url):
            continue
        articles.append({
            'id': str(a.get('id') or a.get('dataSourceIdentifier') or url),
            'headline': a['headline'],
            'description': a.get('description'),
            'published': a.get('published'),
            'url': url,
            'type': a.get('type'),
            'source': 'ESPN',
        })
    return articles


def format_news_post(article):
    return f"📰 {config.TEAM_NAME} news\n\n{article['headline']}\n\n{article['url']}"


def should_post():
    if get_last_post_date(POST_TYPE) == today_str():
        logging.info("News has already been posted today. Skipping.")
        return False
    hour = now_local().hour
    if 8 <= hour <= 21:
        return True
    logging.info(f"Outside news posting hours (hour: {hour}). Skipping.")
    return False


def main():
    parser = argparse.ArgumentParser(description=f"Fetch {config.TEAM_NAME} news and optionally post to Bluesky.")
    parser.add_argument("--post", action="store_true", help="Post the newest unposted headline to Bluesky.")
    parser.add_argument("--force", action="store_true", help="Ignore the time window and daily limit.")
    parser.add_argument("--no-save", action="store_true", help="Don't write the headlines file.")
    args = parser.parse_args()

    articles = fetch_news()
    if not args.no_save:
        save_outputs(articles, "fulham_news", "news")
    if not articles:
        logging.info("No articles found.")
        return

    posted = set(get_posted_ids("posted_news"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    fresh = [a for a in articles
             if a['id'] not in posted and a['type'] != 'Media'
             and a['published'] and datetime.fromisoformat(a['published'].replace('Z', '+00:00')) >= cutoff]
    if not fresh:
        logging.info(f"No unposted headlines from the last {MAX_AGE_HOURS} hours.")
        return
    post_text = format_news_post(fresh[0])
    print("--- Generated Post ---")
    print(post_text)

    if not args.post:
        logging.info("Dry run: --post flag not provided. Not posting to Bluesky.")
        return
    if not args.force and not should_post():
        return
    if post_to_bluesky(post_text):
        add_posted_id("posted_news", fresh[0]['id'])
        set_last_post_date(POST_TYPE)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)
