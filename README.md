# Fulham Team Tracker

This repository feeds **Fulham Data Bot**, an auto-updating dashboard about Fulham FC's Premier League season. It is the football sibling of [Brewers Data Bot](https://github.com/twallac10/mkebrewers-bot), which is a fork of [Matt Stiles](https://mattstiles.me/)' [Dodgers Data Bot](https://dodgersdata.bot/). It uses the same architecture:

- **Python scripts** fetch and process the data.
- **AWS S3** stores every output and the Bluesky bot's state.
- **Jekyll** (Minimal Mistakes theme) with **D3.js** charts builds the site.
- **GitHub Actions** runs everything inside a shared Docker image.
- **GitHub Pages** hosts the site.

Data comes from two free, keyless public feeds:

| Source | Used for |
|---|---|
| [ESPN soccer API](https://www.espn.com/soccer/club/_/id/370/fulham) | League table, Fulham results and fixtures, every Premier League season since 2001-02, squad list, lineups and goalscorers, news |
| [Fantasy Premier League API](https://fantasy.premierleague.com/) | Player stats (goals, assists, xG, xA, minutes, cards, saves…), all league fixtures for the matchweek-by-matchweek table, injury/suspension news |

This is a non-commercial fan project with no connection to Fulham Football Club or the Premier League.

## What's on the site

- **Dashboard** (`index.markdown`):
  - Headline summary and season stat cards: position, points and gap to the drop zone, W-D-L, form, projected points, and points against the same stage of past seasons.
  - Match-by-match goal difference chart.
  - "Points race" chart comparing this season with every Premier League season since 2001-02.
  - League position after each matchweek.
  - Last five results and next five fixtures.
  - The full league table.
  - Attack and defence cards.
  - Fulham's final position in every Premier League season.
  - Latest headlines.
- **Players** (`players.md`): sortable, heat-shaded tables of attacking, defending and discipline stats.
- **Squad** (`squad.md`): squad cards by position, plus the current injury and suspension list.

## Automated Bluesky posts

| Script | Workflow | What it posts |
|---|---|---|
| `scripts/10_post_matchday.py` | `post_matchday.yml` (every 15 min) | On match days: a **preview** (kickoff, venue, both clubs' positions), the **starting XI** once announced, and the **full-time result** with scorers and the new league position |
| `scripts/09_post_weekly_reports.py` | `post_weekly_reports.yml` (daily, 10am UK) | **Table** check-in Mondays, **attack** report Wednesdays, **defence** report Thursdays |
| `scripts/08_fetch_news.py --post` | `post_news.yml` | The newest Fulham headline from the last 48 hours, at most once a day |
| `scripts/11_post_availability.py` | `post_availability.yml` | New injury/suspension news. This is the football version of the Brewers bot's transactions posts |

Every post is checked against Bluesky's 300-character limit, and links are clickable. Each post is posted once only: the IDs or dates of posted updates are stored on S3 under `fulhamfc/data/bluesky/`.

## How it works

`fetch.yml` runs every three hours during the season (August to May) and daily in the summer. It runs these scripts in order:

| Script | Output (`data/`, `_data/` and S3) |
|---|---|
| `01_fetch_league_table.py` | `standings/league_table` |
| `02_fetch_matches.py` | `matches/fulham_matches_current`, `matches/fulham_schedule` |
| `03_build_table_progression.py` | `standings/table_by_gameweek` |
| `04_fetch_player_stats.py` | `players/fulham_players_current`, `players/fulham_team_stat_ranks` |
| `05_fetch_squad.py` | `squad/fulham_squad_current`, `squad/fulham_availability` |
| `06_fetch_historical_seasons.py` | `history/fulham_pl_history_matches`, `history/fulham_pl_seasons` (cached on S3; rebuilt weekly by `fetch_historical.yml`) |
| `07_create_toplines_summary.py` | `standings/season_summary_latest` |
| `08_fetch_news.py` | `news/fulham_news` |

The workflow then builds the Jekyll site and deploys it to the `gh-pages` branch. The pages read the generated `_data/*.json` files at build time, so the site needs no runtime data requests.

Shared code lives in `scripts/config.py` (team, season, S3 settings), `scripts/common.py` (HTTP, saving, S3, Bluesky), `scripts/espn.py` and `scripts/fpl.py`.

### Data quality notes

- ESPN's feed for 2009-10 lists most matches twice, under newer event IDs with wrong scores. `espn.dedupe_league_matches` keeps the original event for each fixture.
- Season totals are checked against ESPN's official final table. Where they differ, the official numbers win and the run logs a warning. Today only 2002-03 differs, by one result. ESPN has no 2001-02 table, so that season shows no final position.
- The matchweek table separates teams level on points by goal difference, then goals scored. The Premier League's later tie-breakers aren't modelled.

## Running locally

```bash
pip install -r requirements.txt
export PYTHONPATH=$PWD

# Without AWS credentials (or with SKIP_S3=1) scripts write local files only
SKIP_S3=1 python scripts/01_fetch_league_table.py
SKIP_S3=1 python scripts/02_fetch_matches.py
# ... 03-08 in order

# Dry-run the bots (nothing is posted without --post)
SKIP_S3=1 python scripts/10_post_matchday.py --event-id 401879318 --stage result
SKIP_S3=1 python scripts/09_post_weekly_reports.py --type table --dry-run

python -m pytest -q

bundle install
bundle exec jekyll serve   # http://localhost:4000/fulhamfc-bot/
```

## Setup

See [SETUP.md](SETUP.md) for the one-time setup: S3 bucket, IAM user, GitHub secrets, Pages and the Bluesky account. See [SEASON_TRANSITION.md](SEASON_TRANSITION.md) for what to change each summer.

## Data storage and access

Outputs are uploaded to `s3://fulhamfc-data/fulhamfc/data/<folder>/<name>.{json,csv}`, for example:

- `standings/league_table.json`
- `standings/season_summary_latest.json`
- `matches/fulham_matches_current.json`
- `players/fulham_players_current.json`
- `history/fulham_pl_history_matches.json`

If the bucket policy allows public reads (see SETUP.md), they are also available at `https://fulhamfc-data.s3.amazonaws.com/fulhamfc/data/...`.

## License

MIT. See [LICENSE](LICENSE). The original Dodgers Data Bot code is © Matt Stiles.
