# Fulham Data Bot: setup guide

One-time steps to get the pipeline, site and Bluesky bot running. They mirror the Brewers bot's setup. If you already have the Brewers AWS account, you can reuse the same IAM user and add a new bucket.

## 1. AWS S3

1. Create a bucket named **`fulhamfc-data`** in **`us-east-2`**. If you use a different name or region, update `S3_BUCKET` / `AWS_REGION` in `scripts/config.py` and `aws-region` in `.github/workflows/*.yml`.
2. (Optional) To make the data files publicly downloadable, turn off "Block all public access" and add this bucket policy. The site doesn't need it, because pages are built from the data at build time.

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "PublicReadData",
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::fulhamfc-data/fulhamfc/data/*"
     }]
   }
   ```

   The bot's state files live under `fulhamfc/data/bluesky/`. To keep those private, narrow the resource to the folders you want public.
3. Create an IAM user (e.g. `github-actions-fulhamfc-bot`). Give it read/write access to the bucket, either with `AmazonS3FullAccess` or with a policy limited to `arn:aws:s3:::fulhamfc-data/*`. Create an access key for it.

## 2. GitHub repository secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | The IAM user's access key |
| `AWS_SECRET_ACCESS_KEY` | The IAM user's secret key |
| `BLUESKY_HANDLE` | The bot's handle, e.g. `fulhamfc-bot.bsky.social` |
| `BLUESKY_APP_PASSWORD` | An app password from [bsky.app/settings/app-passwords](https://bsky.app/settings/app-passwords) (not the account password) |

Without the Bluesky secrets, the posting workflows log an error and post nothing. Everything else still runs.

## 3. Build the Docker image (first run only)

The workflows run inside `ghcr.io/twallac10/fulhamfc-bot:latest`. `build-image.yml` builds it whenever `Dockerfile`, `requirements.txt` or the Gemfiles change on `main`. On a brand-new repo, run **Actions → Build and Push Docker Image → Run workflow** once and wait for it to finish before running `fetch`. If the package is private, give the repository access to it under the package's settings.

## 4. GitHub Pages

1. Run **Actions → fetch → Run workflow**. Its first successful run creates the `gh-pages` branch.
2. **Settings → Pages → Build and deployment → Deploy from a branch → `gh-pages` / root.**
3. Under **Custom domain**, enter `fulhamfc.bot` (it's also in the `CNAME` file, which is deployed with the site). Once DNS resolves, tick **Enforce HTTPS**.

The repository must be public for free Pages hosting and unlimited Actions minutes. The match-day workflow runs every 15 minutes.

### DNS for fulhamfc.bot

At the domain registrar, add these records:

```
Type    Name    Value
A       @       185.199.108.153
A       @       185.199.109.153
A       @       185.199.110.153
A       @       185.199.111.153
CNAME   www     twallac10.github.io
```

Check with `dig fulhamfc.bot +short`. It should list the four GitHub Pages IPs. It can take up to an hour to propagate, and GitHub then issues the HTTPS certificate. (`.bot` domains require HTTPS, so the site won't load over plain HTTP until the certificate is issued.)

The domain is configured in three places: `CNAME`, `url` in `_config.yml`, and `SITE_URL` in `scripts/config.py` (used for links in Bluesky posts). If the domain ever changes, update all three.

## 5. Bluesky account

1. Create the account (e.g. `fulhamfc-bot.bsky.social`) and set `bluesky_handle` in `_config.yml` for the footer link.
2. Create an app password and add both secrets (step 2).
3. Test without posting, locally or via `workflow_dispatch` on a branch:

   ```bash
   SKIP_S3=1 PYTHONPATH=$PWD python scripts/09_post_weekly_reports.py --type table --dry-run
   SKIP_S3=1 PYTHONPATH=$PWD python scripts/10_post_matchday.py --event-id <espn id> --stage preview
   ```

## 6. Workflows at a glance

| Workflow | Schedule (UTC) | Purpose |
|---|---|---|
| `fetch.yml` | every 3h Aug-May, daily Jun-Jul, on push to main | Data pipeline, site build and deploy |
| `fetch_historical.yml` | Sundays 06:00 | Full rebuild of the Premier League history cache |
| `post_matchday.yml` | every 15 min, 07:00-22:45 | Preview, XI and result on match days |
| `post_weekly_reports.yml` | daily 09:00 | Table (Mon), attack (Wed), defence (Thu) reports |
| `post_news.yml` | 09:00, 13:00, 17:00 | One fresh headline a day |
| `post_availability.yml` | every 3h from 08:30 | New injury/suspension news |
| `tests.yml` | push / pull request | Unit tests |
| `build-image.yml` | Dockerfile / dependency changes | Rebuild the shared image |

Cron runs in UTC. UK times shift by an hour when the clocks change, and the scripts handle UK time themselves.
