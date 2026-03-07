# HypeX

**TradingView for comics hype** — track hype index and price series for the top 1,000 manga/manhwa/manhua/webtoons.

## Structure

```
HypeX/
├── apps/
│   ├── api/          # FastAPI backend
│   ├── worker/       # Python worker/CLI (daily metrics)
│   └── web/          # Next.js frontend
├── packages/
│   ├── core/         # Shared Python: registry, resolver, loader
│   └── sources/      # Plugin-based ingestion (packages/sources/*)
├── data/
│   └── registry/     # titles.csv, aliases.json
├── docs/             # Architecture, data model
├── scripts/          # bootstrap.sh, lint.sh, check-structure.sh
├── docker-compose.yml
├── .env.example
├── Makefile
└── pyproject.toml
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for data flow and plugin system, and [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for Postgres schema.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+
- Docker (for Postgres)

## Quick Start (Bootstrap)

```bash
./scripts/bootstrap.sh
```

This sets up env, installs deps, starts Postgres, runs the worker once, and prints dev instructions.

## Setup (Manual)

1. **Install Python deps**

   With uv:
   ```bash
   cd HypeX
   uv sync
   ```

   Or with pip/venv:
   ```bash
   cd HypeX
   python -m venv .venv
   .venv/bin/pip install -e packages/core
   .venv/bin/pip install fastapi uvicorn psycopg[binary] pydantic
   ```

2. **Start Postgres**

   ```bash
   make db-up
   ```

3. **Run worker to populate DB** (generates synthetic metrics)

   ```bash
   make worker
   # Or for a specific date:
   uv run python -m apps.worker.run --date 2025-02-28
   ```

4. **Configure env**

   ```bash
   cp .env.example .env
   # Edit .env if needed (DATABASE_URL, NEXT_PUBLIC_API_URL)
   ```

5. **Install web deps**

   ```bash
   cd apps/web && npm install
   ```

## Run

**Terminal 1 – API**

```bash
make dev-api
# → http://localhost:8000
# → http://localhost:8000/docs (OpenAPI)
```

**Terminal 2 – Web**

```bash
make dev-web
# → http://localhost:3000
```

Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env` or `apps/web/.env.local`.

## API Endpoints

| Route | Description |
|-------|-------------|
| `GET /titles` | List titles (pagination, search, medium filter) |
| `POST /resolve` | Resolve text to candidate titles |
| `GET /series/{canonical_id}` | Title info + price series |

## Sync Titles

Sync registry to Postgres:

```bash
python -m apps.worker.sync_titles
```

See [docs/REGISTRY.md](docs/REGISTRY.md) for CSV schema and sync behavior.

## Test

```bash
make test
```

This runs the repo structure check (`scripts/check-structure.sh`), Python tests, and web build.

Or individually:

```bash
# Python (core resolver)
uv run pytest packages/core/tests -v

# Web build
cd apps/web && npm run build
```

## Format & Lint

```bash
make fmt
# Or run full lint:
./scripts/lint.sh
# Or: npm run lint
```

## Commands to Run Locally

```bash
# 1. Install deps
uv sync
cd apps/web && npm install

# 2. Start Postgres
make db-up

# 3. Populate DB with synthetic data
make worker

# 4. Start API (terminal 1)
make dev-api

# 5. Start Web (terminal 2)
make dev-web
```

Then open http://localhost:3000 for the app and http://localhost:8000/docs for the API.
