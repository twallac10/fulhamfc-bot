#!/usr/bin/env python
# coding: utf-8

"""
Matchday posts for Bluesky
Runs every few minutes through the day. On a Fulham matchday it posts, once
each and in order:

    preview  - opponent, kickoff time, venue and both clubs' league positions
    lineup   - the starting XI and formation, once ESPN publishes it (~1 hour
               before kickoff)
    result   - the full-time score, goalscorers and Fulham's new league position

Already-posted stages are tracked on S3, so repeated runs never double post.
"""

import argparse
import logging
import sys
from datetime import timedelta

from scripts import config
from scripts.common import add_posted_id, get_posted_ids, now_local, ordinal, post_to_bluesky, to_local
from scripts.espn import fetch_standings, fetch_summary, fetch_team_matches, goal_events, starting_lineup

STATE = "posted_matchday"
LINEUP_WINDOW = timedelta(minutes=90)   # start looking for the XI this long before kickoff
EARLIEST_PREVIEW_HOUR = 8


def fixture_title(match):
    if match['home_away'] == 'home':
        return f"{config.TEAM_NAME} vs {match['opponent']}"
    return f"{match['opponent']} vs {config.TEAM_NAME}"


def table_line(standings, team_id):
    row = next((r for r in standings if r['team_id'] == str(team_id)), None)
    if not row:
        return None
    return f"{row['team_short']}: {ordinal(row['position'])}, {row['points']} pts"


def format_preview(match, standings):
    kickoff = to_local(match['kickoff_utc'])
    when = kickoff.strftime('%H:%M') + " UK" if match['time_valid'] else "time TBC"
    lines = [f"🏟️ Matchday! {fixture_title(match)}", "", f"⏰ {when}"]
    if match.get('venue'):
        lines.append(f"📍 {match['venue']}")
    table = [t for t in (table_line(standings, config.ESPN_TEAM_ID), table_line(standings, match['opponent_id'])) if t]
    if table:
        lines += ["", *table]
    return "\n".join(lines)


def format_lineup(match, formation, lines):
    shape = f" ({formation})" if formation else ""
    xi = "; ".join(", ".join(line) for line in lines)
    return f"📋 {config.TEAM_NAME} XI vs {match['opponent']}{shape}:\n\n{xi}"


def format_result(match, goals, standings, matches_played):
    home = match['home_away'] == 'home'
    h_name, a_name = (config.TEAM_NAME, match['opponent']) if home else (match['opponent'], config.TEAM_NAME)
    h_goals, a_goals = (match['goals_for'], match['goals_against']) if home else (match['goals_against'], match['goals_for'])
    emoji = {'W': '✅', 'D': '🤝', 'L': '❌'}[match['result']]
    lines = [f"{emoji} FT: {h_name} {h_goals}-{a_goals} {a_name}"]
    ours = [g for g in goals if g['team_id'] == config.ESPN_TEAM_ID]
    if ours:
        scorers = []
        for g in ours:
            tag = " (pen)" if g['penalty'] else " (og)" if g['own_goal'] else ""
            scorers.append(f"{g['scorer'] or 'Unknown'} {g['minute'] or ''}{tag}".strip())
        lines += ["", f"⚽ {', '.join(scorers)}"]
    # Only quote the table once it includes this result
    row = next((r for r in standings if r['team_id'] == config.ESPN_TEAM_ID), None)
    if row and row['played'] == matches_played:
        lines += ["", f"{config.TEAM_NAME} are now {ordinal(row['position'])} with {row['points']} pts"]
    lines += ["", f"More: {config.SITE_URL}"]
    return "\n".join(lines)


def todays_match(matches, today):
    return next((m for m in matches if m['date'] == today
                 and m['status'] not in ('STATUS_POSTPONED', 'STATUS_CANCELED')), None)


def next_stage(match, now, posted):
    """Which post (if any) is due for this match right now."""
    eid = match['event_id']
    kickoff = to_local(match['kickoff_utc'])
    if match['completed'] and match['result']:
        return 'result' if f"result_{eid}" not in posted else None
    if f"preview_{eid}" not in posted and now < kickoff and now.hour >= EARLIEST_PREVIEW_HOUR:
        return 'preview'
    if f"lineup_{eid}" not in posted and kickoff - LINEUP_WINDOW <= now <= kickoff + timedelta(minutes=30):
        return 'lineup'
    return None


def main():
    parser = argparse.ArgumentParser(description=f"Post {config.TEAM_NAME} matchday updates to Bluesky.")
    parser.add_argument("--post", action="store_true", help="Publish to Bluesky (otherwise dry run).")
    parser.add_argument("--event-id", help="Use this ESPN match instead of today's (for testing).")
    parser.add_argument("--stage", choices=['preview', 'lineup', 'result'], help="Force a stage (for testing).")
    args = parser.parse_args()

    now = now_local()
    matches = fetch_team_matches(config.SEASON_START_YEAR)
    if args.event_id:
        match = next((m for m in matches if m['event_id'] == args.event_id), None)
    else:
        match = todays_match(matches, now.strftime('%Y-%m-%d'))
    if not match:
        logging.info("No match today.")
        return

    posted = set(get_posted_ids(STATE))
    stage = args.stage or next_stage(match, now, posted)
    logging.info(f"{fixture_title(match)} ({match['status']}): stage = {stage}")
    if not stage:
        return

    if stage == 'lineup':
        formation, lines = starting_lineup(fetch_summary(match['event_id']))
        if sum(len(line) for line in lines) < 11:
            logging.info("Starting XI not published yet.")
            return
        text = format_lineup(match, formation, lines)
    elif stage == 'result':
        goals = goal_events(fetch_summary(match['event_id']))
        played = sum(1 for m in matches if m['result'] and m['kickoff_utc'] <= match['kickoff_utc'])
        text = format_result(match, goals, fetch_standings(config.SEASON_START_YEAR)['rows'], played)
    else:
        text = format_preview(match, fetch_standings(config.SEASON_START_YEAR)['rows'])

    print(f"--- {stage} post ---\n{text}")
    if not args.post:
        logging.info("Dry run: --post flag not provided. Not posting to Bluesky.")
        return
    if post_to_bluesky(text):
        add_posted_id(STATE, f"{stage}_{match['event_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)
