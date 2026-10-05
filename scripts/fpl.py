"""
Helpers for the Fantasy Premier League API (player stats, all league fixtures).
"""

from scripts import config
from scripts.common import FPL_API, get_json

POSITIONS = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}
POSITION_GROUPS = {1: 'Goalkeepers', 2: 'Defenders', 3: 'Midfielders', 4: 'Forwards'}
STATUS_LABELS = {
    'a': 'Available',
    'd': 'Doubtful',
    'i': 'Injured',
    's': 'Suspended',
    'u': 'Unavailable',
    'n': 'Not in squad',
}


def bootstrap():
    return get_json(f"{FPL_API}/bootstrap-static/")


def fixtures():
    return get_json(f"{FPL_API}/fixtures/")


def team_id(bootstrap_data, name=config.FPL_TEAM_NAME):
    for team in bootstrap_data['teams']:
        if team['name'] == name:
            return team['id']
    raise ValueError(f"Team {name!r} not found in FPL data. Is it in the Premier League this season?")
