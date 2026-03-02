# World News Map

Live Demo: [World News Map](https://zhongyao.li)

World News Map is a Python pipeline that fetches recent world events from Wikipedia, enriches them with POI + coordinates, and publishes static map data.

This branch is the server deployment version.

For the Github Pages deployment version, see [https://github.com/jackgdn/world-news-map](https://github.com/jackgdn/world-news-map).

## Features

- Fetches recent events from Wikipedia Portal: Current events
- Extracts one core POI per event using an LLM
- Geocodes POIs via Nominatim (OpenStreetMap)
- Produces static files under public/
  - public/news/*.json
  - public/robots.txt
  - public/sitemap.xml
  - public/.well-known/security.txt

## How this version runs

- `src/main.py` starts both backend and frontend processes.
- Backend (`src/backend/run_backend.py`) performs an initial refresh, then runs scheduled refresh tasks every `update_interval_hours`.
- Frontend (`src/frontend/run_frontend.py`) serves static files from `public/` with path allowlist, IP blocklist, and optional HTTPS.

## Repository structure

```text
.
├─ config.template.yaml
├─ config.yaml
├─ prompt.txt
├─ requirements.txt
├─ public/
├─ cache/
├─ logs/
└─ src/
   ├─ main.py
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
      ├─ run_frontend.py
      └─ clean_news.py
```

## Configuration

Copy and edit config:

```bash
cp config.template.yaml config.yaml
```

PowerShell:

```powershell
Copy-Item config.template.yaml config.yaml
```

`config.yaml` field reference:

| Key                                 | Required | Description                                                                 |
| ----------------------------------- | -------- | --------------------------------------------------------------------------- |
| `request_interval`                  |          | Delay (seconds) between external requests.                                  |
| `request_timeout`                   |          | HTTP timeout (seconds) for upstream calls.                                  |
| `max_retries`                       |          | Retry count for LLM/remote request failures.                                |
| `contact_info`                      | Yes      | Contact string used in request headers (recommended: email or project URL). |
| `language_model_base_url`           | Yes      | LLM API base URL.                                                           |
| `language_model_name`               | Yes      | Model name used for POI extraction.                                         |
| `language_model_api_key`            | Yes      | API key for the selected LLM endpoint.                                      |
| `language_model_extra_params`       |          | Extra request body options passed to the LLM API.                           |
| `log_level`                         |          | Log verbosity (`debug`, `info`, `warning`, `error`, `critical`).            |
| `log_description_max_length`        |          | Max description length shown in log previews.                               |
| `cache_expiration_days`             |          | Coordinate cache retention period.                                          |
| `update_interval_hours`             |          | Backend refresh interval in hours.                                          |
| `http_server_host`                  |          | Bind host (`localhost` or `0.0.0.0`).                                       |
| `http_server_port`                  |          | Listening port for the frontend HTTP server.                                |
| `base_url`                          | Yes      | Public site base URL used for generated metadata links.                     |
| `connection_timeout_seconds`        |          | Socket timeout per client connection.                                       |
| `http_listen_backlog`               |          | Max pending TCP connections.                                                |
| `reload_blocklist_interval_seconds` |          | Interval to reload banned IP list from file.                                |
| `https_certificate_path`            |          | TLS certificate path. Leave empty to disable HTTPS.                         |
| `https_key_path`                    |          | TLS private key path. Leave empty to disable HTTPS.                         |

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend + frontend together:

```bash
python src/main.py
```

Run only backend:

```bash
python src/backend/run_backend.py
```

Run only frontend:

```bash
python src/frontend/run_frontend.py
```

## Development Tips

- Use a virtual environment (`.venv`) and pin dependency changes in `requirements.txt`.
- During debugging, set `log_level: "debug"` in `config.yaml` to inspect fetch/parse/geocode behavior.
- You can run scripts either as direct files or as Python modules.
- Tune extraction quality by iterating on `prompt.txt` and testing with a small batch first.
- If coordinate results look stale, clear `cache/coordinate.msgpack` and re-run backend refresh.
- Keep `contact_info` valid and descriptive to reduce upstream request rejection risk.
- Run backend and frontend separately during troubleshooting to isolate failures faster.
- Before production rollout, verify:
  - `base_url` matches your public domain
  - HTTPS cert/key paths are valid (if HTTPS is enabled)
  - `public/news/`, `sitemap.xml`, and `.well-known/security.txt` are generated correctly
