# Configuration for Fulham Dashboard Scripts

TEAM_NAME = "Fulham"
TEAM_FULL_NAME = "Fulham FC"
TEAM_NICKNAME = "Cottagers"
TEAM_ABBR = "FUL"
TEAM_HOME_GROUND = "Craven Cottage"
TEAM_TIMEZONE = "Europe/London"
TEAM_EMOJI = "⚪⚫"

# Source identifiers
ESPN_TEAM_ID = "370"         # https://www.espn.com/soccer/club/_/id/370/fulham
ESPN_LEAGUE = "eng.1"        # Premier League
FPL_TEAM_NAME = "Fulham"     # Fantasy Premier League team name (id is resolved at runtime)

LEAGUE_NAME = "Premier League"
LEAGUE_MATCHES = 38

# Season/Year Configuration
# Seasons are identified by the calendar year they start in (2026 = 2026-27).
# Update this in the summer once the new season's fixtures are published.
# See SEASON_TRANSITION.md.
SEASON_START_YEAR = 2026

# First season to include in the historical Premier League comparisons.
# ESPN has Premier League match data back to 2001-02.
HISTORY_START_YEAR = 2001

# Public site (used in Bluesky posts)
SITE_URL = "https://twallac10.github.io/fulhamfc-bot"

# AWS S3 Configuration
S3_BUCKET = "fulhamfc-data"
S3_PREFIX = "fulhamfc"
AWS_REGION = "us-east-2"

# File path patterns
DATA_DIR = "data"            # local copies of every output (gitignored)
JEKYLL_DATA_DIR = "_data"    # outputs the site reads at build time (gitignored)


def season_label(start_year=SEASON_START_YEAR):
    """2026 -> '2026-27'."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"
