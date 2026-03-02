# World News Map

Live Demo: [World News Map](https://newsmap.zhongyao.li)

World News Map is a Python pipeline that fetches recent world events from Wikipedia, enriches them with POI + coordinates, and publishes static map data.

This branch is designed to run on GitHub Actions and deploy to GitHub Pages.

For the server deployment version, see [https://github.com/jackgdn/world-news-map/tree/master](https://github.com/jackgdn/world-news-map/tree/master).

## Features

- Fetches recent events from Wikipedia Portal: Current events
- Extracts one core POI per event using an LLM
- Geocodes POIs via Nominatim (OpenStreetMap)
- Produces static files under public/
  - public/news/*.json
  - public/robots.txt
  - public/sitemap.xml
  - public/.well-known/security.txt

## Deployment model (actual behavior on this branch)

The workflow file is .github/workflows/update-news.yml.

- Trigger:
  - Scheduled: 0 6,18 * * * (UTC)
  - Manual: workflow_dispatch
- Runtime: ubuntu-latest, Python 3.10
- Flow:
  1. Restore previous news/cache from gh-pages branch
  2. Clean old news via src/frontend/clean_news.py
  3. Run backend pipeline via src/backend/run_backend.py
  4. Force-push generated public content to gh-pages

Published gh-pages content includes:

- public/* (site files)
- cache/
- .well-known/
- .nojekyll
- CNAME (if present in repository root)

## Required GitHub Secrets

Set these repository secrets before enabling the workflow:

- LANGUAGE_MODEL_BASE_URL
- LANGUAGE_MODEL_NAME
- LANGUAGE_MODEL_API_KEY
- BASE_URL

Notes:

- CONTACT_INFO is set by workflow as `https://github.com/${{ github.actor }}`.
- The workflow validates required secrets before running the pipeline.

## Repository structure

```text
.
├─ .github/workflows/update-news.yml
├─ config.yaml
├─ prompt.txt
├─ requirements.txt
├─ public/
├─ cache/
├─ logs/
└─ src/
   ├─ backend/
   │  ├─ run_backend.py
   │  ├─ fetch_news.py
   │  ├─ fetch_poi.py
   │  ├─ fetch_coord.py
   │  ├─ generate_metadata.py
   │  ├─ utils.py
   │  └─ config.py
   ├─ common/
   └─ frontend/
      └─ clean_news.py
```

## Run from a fork (GitHub Actions + GitHub Pages)

1. Fork this repository to your own GitHub account.
2. In your fork, open **Settings → Secrets and variables → Actions** and add:
  - `LANGUAGE_MODEL_BASE_URL`
  - `LANGUAGE_MODEL_NAME`
  - `LANGUAGE_MODEL_API_KEY`
  - `BASE_URL` (your GitHub Pages URL)
3. Open **Settings → Pages** and set source to branch `gh-pages` (root).
4. Open **Actions**, enable workflows if prompted, then open **Update News**.
5. Click **Run workflow** once for initial deployment (or wait for the schedule).
6. After the job succeeds, visit your GitHub Pages site URL.
