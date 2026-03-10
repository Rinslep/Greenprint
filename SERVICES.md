# Greenprint — Services & Deployment Reference

This document describes every external service, runtime dependency, environment variable, and
infrastructure component that Greenprint uses. It is intended to be passed to an LLM or read by a
developer who is setting up a deployment.

---

## 1. Runtime Services

### 1.1 FastAPI / Uvicorn (Web API)

| Property | Value |
|---|---|
| Framework | FastAPI ≥ 0.100 |
| Server | Uvicorn (standard extras) ≥ 0.23 |
| Default host | `127.0.0.1` |
| Default port | `8000` |
| Rate limiting | slowapi ≥ 0.1.9 (per-IP, configurable) |

The API exposes all endpoints under `/v1/`. Start it with:

```
python -m greenprint serve
python -m greenprint serve --host 0.0.0.0 --port 8000
```

For production, put Uvicorn behind a reverse proxy (nginx, Caddy, etc.) and set `--host 0.0.0.0`.

---

### 1.2 SQLite / PostgreSQL (Primary Database)

| Property | Value |
|---|---|
| Default engine | SQLite |
| Default path | `./blueprints.db` (relative to project root) |
| ORM | SQLAlchemy ≥ 2.0 |
| Migrations | Alembic ≥ 1.12 (config in `alembic.ini`, migrations in `storage/migrations/`) |

Switch to PostgreSQL by changing `DB_URL` in `.env`:

```
DB_URL=postgresql+psycopg2://user:password@host:5432/greenprint
```

SQLAlchemy's `JSON` type becomes `JSONB` automatically on PostgreSQL.

During development the schema is created with `create_all()`. Before the first public deployment
the project intends to switch fully to Alembic migrations (the `storage/migrations/` directory is
already scaffolded).

**Tables created at startup:**

| Table | Purpose |
|---|---|
| `blueprints` | All decoded, validated blueprint records |
| `motifs` | Canonical production-layout patterns |
| `blueprint_motifs` | Junction — which blueprints contain which motifs |
| `review_queue_items` | Blueprints that need manual recipe review |

---

### 1.3 SQLite (Scraper Progress Tracker)

A separate SQLite file records which URLs have already been fetched so scraper runs are
resumable after interruption.

| Property | Value |
|---|---|
| Default path | `./scraper_progress.db` (project root) |
| Config key | `SCRAPER_PROGRESS_DB` |

---

## 2. External APIs and Scraped Sources

### 2.1 FactorioPrints.com / Factorio.school — Firebase Realtime Database

These two websites share one Firebase Realtime Database backend.

| Property | Value |
|---|---|
| Firebase project ID | `facorio-blueprints` *(missing the second 't' in "Factorio")* |
| Base URL | `https://facorio-blueprints.firebaseio.com` |
| Auth required | No (public read) |
| Recommended delay | 0.5–1 s between requests |

Endpoints used:

```
GET /blueprints.json?orderBy="$key"&limitToFirst=100&startAt="<cursor>"
GET /blueprints/{id}.json
GET /byTag/version/1,1.json
```

No API key is needed. The site owner pays for Firebase, so the scraper honours rate limits.

---

### 2.2 Reddit — r/factorio

| Property | Value |
|---|---|
| Library | PRAW ≥ 7.7 |
| Target subreddit | `r/factorio` |
| Rate limit | 60 requests/minute (Reddit's OAuth limit) |
| Auth required | **Yes — OAuth2 credentials required** |

Required environment variables (all three must be set):

| Variable | Description |
|---|---|
| `REDDIT_CLIENT_ID` | App client ID from reddit.com/prefs/apps |
| `REDDIT_CLIENT_SECRET` | App client secret |
| `REDDIT_USER_AGENT` | Arbitrary string, e.g. `greenprint/0.1 by u/yourname` |

To create Reddit credentials: go to https://www.reddit.com/prefs/apps, create a "script" app,
and copy the client ID (below the app name) and client secret.

---

### 2.3 Factorio Forums — forums.factorio.com

| Property | Value |
|---|---|
| Library | httpx ≥ 0.25 + BeautifulSoup4 ≥ 4.12 |
| Auth required | No (public read) |
| robots.txt | Checked before every new domain |

Target subforums scraped:

| Forum ID | Name |
|---|---|
| 8 | Show your Creations |
| 194 | Mechanical Throughput Magic |
| 193 | Combinator Creations |

---

## 3. Environment Variables

All variables are read from a `.env` file in the project root (or from the real environment).
Create the file by copying the table below.

| Variable | Default | Required | Description |
|---|---|---|---|
| `DB_URL` | `sqlite:///./blueprints.db` | No | SQLAlchemy database URL |
| `LOG_LEVEL` | `INFO` | No | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_MODE` | `dev` | No | `dev` (pretty) or `json` (structured JSON logs) |
| `SCRAPER_RATE_LIMIT_DELAY` | `1.0` | No | Seconds to wait between scraper requests |
| `SCRAPER_PROGRESS_DB` | `<project_root>/scraper_progress.db` | No | Path to scraper resumability database |
| `REDDIT_CLIENT_ID` | *(empty)* | **Yes, for Reddit scraper** | Reddit OAuth app client ID |
| `REDDIT_CLIENT_SECRET` | *(empty)* | **Yes, for Reddit scraper** | Reddit OAuth app client secret |
| `REDDIT_USER_AGENT` | *(empty)* | **Yes, for Reddit scraper** | Reddit user agent string |
| `API_RATE_LIMIT_PER_MINUTE` | `60` | No | Max API requests per IP per minute |

Minimal `.env` for local development (no Reddit):

```dotenv
DB_URL=sqlite:///./blueprints.db
LOG_LEVEL=INFO
LOG_MODE=dev
```

Minimal `.env` for production with PostgreSQL and Reddit:

```dotenv
DB_URL=postgresql+psycopg2://greenprint:secret@localhost:5432/greenprint
LOG_LEVEL=WARNING
LOG_MODE=json
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=greenprint/0.1 by u/yourname
API_RATE_LIMIT_PER_MINUTE=60
```

---

## 4. Python Version & Package Dependencies

**Python version:** 3.12 (see `.python-version`).

Install all dependencies:

```
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---|---|---|
| pydantic | ≥ 2.0 | Data validation and settings models |
| pydantic-settings | ≥ 2.0 | `.env` / environment variable loading |
| python-dotenv | ≥ 1.0 | `.env` file support |
| networkx | ≥ 3.0 | Crafting graph construction and analysis |
| sqlalchemy | ≥ 2.0 | ORM and database abstraction |
| alembic | ≥ 1.12 | Database schema migrations |
| structlog | ≥ 23.0 | Structured logging |
| rich | ≥ 13.0 | Pretty terminal output |
| fastapi | ≥ 0.100 | REST API framework |
| uvicorn[standard] | ≥ 0.23 | ASGI server |
| slowapi | ≥ 0.1.9 | Rate limiting middleware for FastAPI |
| httpx | ≥ 0.25 | Async HTTP client (forum scraper) |
| beautifulsoup4 | ≥ 4.12 | HTML parsing (forum scraper) |
| praw | ≥ 7.7 | Reddit API client |
| typer | ≥ 0.9 | CLI framework |
| pytest | ≥ 7.0 | Test runner |
| pytest-cov | ≥ 4.0 | Test coverage reporting |

---

## 5. CLI Entry Points

All commands are available via `python -m greenprint <command>`.

| Command | Description |
|---|---|
| `scrape --source <src> [--limit N]` | Scrape blueprints; `--source` is `factorioprints`, `reddit`, or `forums` |
| `ingest --file <path>` | Import blueprint strings from a plain-text file (one per line) |
| `analyse [--id <uuid>] [--all]` | Run/re-run analysis on one or all blueprints |
| `review` | Print unresolved review-queue items |
| `serve [--host H] [--port P]` | Start the FastAPI server (default `127.0.0.1:8000`) |
| `stats` | Print dataset statistics (counts, queue size, etc.) |

---

## 6. Static Reference Data

The `reference/` directory ships with the repository and is **never fetched at runtime**:

| File | Contents |
|---|---|
| `reference/recipes.json` | All vanilla Factorio 1.1 recipe definitions |
| `reference/entities.json` | All vanilla Factorio 1.1 entity metadata |
| `reference/version.json` | Target version metadata (1.1.110) |

These files must be present for the pipeline to run. They are part of the repository — no download
step is needed.

---

## 7. No Containerisation (Yet)

There is currently **no Dockerfile, docker-compose.yml, or cloud deployment configuration** in the
repository. Deployment is manual Python environment setup. A typical sequence:

```bash
# 1. Set up Python 3.12 environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env (see Section 3)
touch .env   # then populate it

# 4. (Optional) create PostgreSQL database and update DB_URL in .env
# createdb greenprint

# 5. Start the API
python -m greenprint serve --host 0.0.0.0 --port 8000

# 6. (Optional) run a scrape
python -m greenprint scrape --source factorioprints --limit 500
```

The database schema is created automatically on first startup — no manual migration step is
required for a fresh install.
