"""
Shared helpers for the Fulham pipeline: HTTP fetching, saving outputs
(locally, for Jekyll and to S3) and Bluesky posting with S3-backed state.
"""

import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from scripts import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/126.0 Safari/537.36'
}

ESPN_SITE_API = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{config.ESPN_LEAGUE}"
ESPN_STANDINGS_API = f"https://site.api.espn.com/apis/v2/sports/soccer/{config.ESPN_LEAGUE}/standings"
FPL_API = "https://fantasy.premierleague.com/api"

BLUESKY_MAX_CHARS = 300


# --- HTTP ---

def get_json(url, params=None, retries=3, backoff=2):
    """GET a JSON document, retrying transient failures."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            logging.warning(f"Request to {url} failed ({e}); retrying in {wait}s")
            time.sleep(wait)


# --- Time ---

def team_tz():
    return ZoneInfo(config.TEAM_TIMEZONE)


def now_local():
    return datetime.now(team_tz())


def today_str():
    return now_local().strftime('%Y-%m-%d')


def to_local(iso_utc):
    """ESPN/FPL timestamps ('2026-09-20T15:30Z') -> aware datetime in team timezone."""
    return pd.Timestamp(iso_utc).tz_convert(config.TEAM_TIMEZONE).to_pydatetime()


# --- Names ---

def normalize_name(name):
    """Lowercase, strip accents and punctuation so names match across sources."""
    if not name:
        return ""
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z ]', '', name.lower()).strip()


def ordinal(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    suffix = 'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


# --- S3 ---

_s3 = None
_s3_checked = False


def get_s3():
    """Return an S3 resource, or None when no AWS credentials are available.

    In GitHub Actions credentials come from aws-actions/configure-aws-credentials.
    Locally the AWS_PERSONAL_PROFILE profile is used if set. Without credentials
    the pipeline still runs and writes local files; uploads are skipped.
    Set SKIP_S3=1 to force that behaviour (local test runs).
    """
    global _s3, _s3_checked
    if _s3_checked:
        return _s3
    _s3_checked = True
    if os.environ.get("SKIP_S3") == "1":
        logging.info("SKIP_S3=1: S3 uploads and reads are disabled.")
        return None
    try:
        import boto3
        profile = os.environ.get("AWS_PERSONAL_PROFILE")
        session = boto3.Session(profile_name=profile, region_name=config.AWS_REGION) if profile \
            else boto3.Session(region_name=config.AWS_REGION)
        if session.get_credentials() is None:
            logging.warning("No AWS credentials found. S3 uploads and reads will be skipped.")
            return None
        _s3 = session.resource("s3")
    except Exception as e:
        logging.warning(f"Could not initialize AWS session: {e}. S3 will be skipped.")
        _s3 = None
    return _s3


def s3_key(subdir, filename):
    return f"{config.S3_PREFIX}/data/{subdir}/{filename}"


def public_url(subdir, filename):
    return f"https://{config.S3_BUCKET}.s3.amazonaws.com/{s3_key(subdir, filename)}"


def upload_file(local_path, key):
    s3 = get_s3()
    if s3 is None:
        return False
    content_types = {'.json': 'application/json', '.csv': 'text/csv', '.parquet': 'application/octet-stream'}
    ext = os.path.splitext(local_path)[1]
    s3.Bucket(config.S3_BUCKET).upload_file(
        local_path, key, ExtraArgs={'ContentType': content_types.get(ext, 'binary/octet-stream')}
    )
    logging.info(f"Uploaded {local_path} to s3://{config.S3_BUCKET}/{key}")
    return True


def read_s3_text(key):
    """Return the object's text, or None if it (or S3) isn't available."""
    s3 = get_s3()
    if s3 is None:
        return None
    from botocore.exceptions import ClientError
    try:
        return s3.Object(config.S3_BUCKET, key).get()['Body'].read().decode('utf-8')
    except ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'):
            return None
        raise


def write_s3_text(key, body, content_type='text/plain'):
    s3 = get_s3()
    if s3 is None:
        logging.warning(f"S3 unavailable; not writing {key}")
        return False
    s3.Object(config.S3_BUCKET, key).put(Body=body, ContentType=content_type)
    return True


# --- Saving outputs ---

def save_outputs(data, name, subdir, formats=("json", "csv"), jekyll=True):
    """Write data (DataFrame, list or dict) to data/<subdir>/, optionally
    _data/<subdir>/ for the site, and upload every format to S3."""
    local_dir = os.path.join(config.DATA_DIR, subdir)
    os.makedirs(local_dir, exist_ok=True)

    if isinstance(data, pd.DataFrame):
        records = json.loads(data.to_json(orient="records", date_format="iso"))
    else:
        records = data

    written = []
    for fmt in formats:
        path = os.path.join(local_dir, f"{name}.{fmt}")
        if fmt == "json":
            with open(path, "w") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
        elif fmt == "csv":
            frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(records)
            frame.to_csv(path, index=False)
        elif fmt == "parquet":
            frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(records)
            frame.to_parquet(path, index=False)
        else:
            raise ValueError(f"Unknown format {fmt}")
        written.append(path)

    if jekyll:
        jekyll_dir = os.path.join(config.JEKYLL_DATA_DIR, subdir)
        os.makedirs(jekyll_dir, exist_ok=True)
        with open(os.path.join(jekyll_dir, f"{name}.json"), "w") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    for path in written:
        upload_file(path, s3_key(subdir, os.path.basename(path)))

    logging.info(f"Saved {name} ({len(records) if hasattr(records, '__len__') else 1} records) to {local_dir}")
    return records


def load_output(name, subdir):
    """Load a JSON output from this run's local files, falling back to S3."""
    path = os.path.join(config.DATA_DIR, subdir, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    text = read_s3_text(s3_key(subdir, f"{name}.json"))
    if text is not None:
        return json.loads(text)
    return None


# --- Bluesky ---

def bluesky_state_key(name):
    return f"{config.S3_PREFIX}/data/bluesky/{name}"


def get_last_post_date(post_type):
    value = read_s3_text(bluesky_state_key(f"last_post_date_{post_type}.txt"))
    return value.strip() if value else None


def set_last_post_date(post_type, date_str=None):
    write_s3_text(bluesky_state_key(f"last_post_date_{post_type}.txt"), date_str or today_str())


def get_posted_ids(name):
    text = read_s3_text(bluesky_state_key(f"{name}.json"))
    if not text:
        return []
    return json.loads(text).get('ids', [])


def add_posted_id(name, post_id, keep=1000):
    ids = [i for i in get_posted_ids(name) if i != post_id]
    ids.append(post_id)
    write_s3_text(bluesky_state_key(f"{name}.json"), json.dumps({'ids': ids[-keep:]}, indent=2),
                  content_type='application/json')


URL_RE = re.compile(r'https?://\S+')


def build_rich_text(text):
    """Return an atproto TextBuilder with every URL turned into a clickable link."""
    from atproto import client_utils
    builder = client_utils.TextBuilder()
    pos = 0
    for match in URL_RE.finditer(text):
        builder.text(text[pos:match.start()])
        builder.link(match.group(0), match.group(0))
        pos = match.end()
    builder.text(text[pos:])
    return builder


def fit_post(text, limit=BLUESKY_MAX_CHARS):
    """Trim a post to Bluesky's limit, cutting whole lines from the end first."""
    if len(text) <= limit:
        return text
    lines = text.split("\n")
    while len(lines) > 1 and len("\n".join(lines)) > limit:
        lines.pop(-1 if not lines[-1].startswith("More:") else -2)
    text = "\n".join(lines).rstrip()
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def post_to_bluesky(text):
    """Publish a post. Returns the post URI, or None on failure / missing credentials."""
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_APP_PASSWORD")
    if not (handle and password):
        logging.error("Bluesky credentials are not set (BLUESKY_HANDLE, BLUESKY_APP_PASSWORD). Cannot post.")
        return None
    text = fit_post(text)
    try:
        from atproto import Client
        client = Client()
        client.login(handle, password)
        response = client.send_post(build_rich_text(text))
        logging.info(f"Post published to Bluesky: {response.uri}")
        return response.uri
    except Exception as e:
        logging.error(f"Failed to post to Bluesky: {e}")
        return None
