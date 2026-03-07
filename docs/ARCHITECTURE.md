# HypeX Architecture

## Monorepo Layout

```
hypex/
├── apps/
│   ├── api/            # FastAPI backend (Python)
│   ├── worker/         # CLI workers: run, ingest, prices, migrate, sync_titles
│   └── web/            # Next.js frontend (TypeScript)
├── packages/
│   ├── core/           # Shared Python: registry, resolver, DB, types
│   └── sources/        # Ingestion plugins
│       ├── reddit/     # Reddit source (PRAW + mock fetcher)
│       └── example/    # TypeScript example stub
├── data/
│   └── registry/       # titles.csv (107 titles), aliases.json
├── docs/
├── scripts/
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

## Data Flow

```
data/registry (titles.csv, aliases.json)
        │
        ▼
packages/core (loader + resolver + DB)
        │
        ├───────────────────────────────────────────┐
        │                                           │
        ▼                                           ▼
apps/worker                                   apps/api
├── sync_titles (registry → DB)               (GET /titles, /health/db)
├── run (synthetic metrics)                   (POST /resolve)
├── ingest (reddit → daily_metrics)           (GET /series/{id})
├── prices (daily_metrics → daily_prices)          │
│       │                                          │ reads
│       │  upserts                                 │
        ▼                                          │
Postgres ◄─────────────────────────────────────────┘
  ├── titles
  ├── daily_metrics    (multi-metric: mentions, engagement, etc.)
  ├── daily_prices     (computed H_t and P_t)
  └── ingest_runs      (idempotency tracking)
        │
        ▼
apps/web (charts + title list)
```

## Ingestion Pipeline

1. **Fetch** — Source plugins fetch raw data (e.g., Reddit posts via PRAW or mock)
2. **Resolve** — Post titles are matched to canonical titles via `resolve_mention()` (score ≥ 0.80)
3. **Aggregate** — Per-title daily metrics: `mentions_count`, `engagement_score`
4. **Store** — Upsert into `daily_metrics` with confidence and source metadata
5. **Track** — `ingest_runs` table ensures idempotency (one run per source per day)

### Reddit Source

- Uses PRAW when `REDDIT_CLIENT_ID` is set, otherwise falls back to a deterministic mock fetcher
- Scans subreddits: manga, manhwa, manhua, webtoons, plus title-specific subs
- CLI: `python -m apps.worker.ingest --source reddit --date YYYY-MM-DD`

## Price Pipeline

Converts raw metrics into stable daily price series:

1. Rolling z-score per metric (28-day window, 7-day minimum)
2. Winsorize to [-3, 3]
3. H_t = 0.7 × z(mentions) + 0.3 × z(engagement)
4. Smooth: Hs_t = 0.7 × H_t + 0.3 × Hs_{t-1}
5. Price: P_t = P_{t-1} × exp(0.02 × Hs_t), P_0 = 100

CLI: `python -m apps.worker.prices --start YYYY-MM-DD --end YYYY-MM-DD`

## API Endpoints

| Route                      | Description                                 |
|---------------------------|---------------------------------------------|
| `GET /titles`             | List titles (pagination, search, medium filter) |
| `POST /resolve`           | Resolve text to candidate titles            |
| `GET /series/{canonical_id}` | Title info + price series                |
| `GET /health/db`          | Database connectivity check                 |

## Key Technologies

- **Python**: FastAPI, psycopg, PRAW, rapidfuzz
- **Postgres**: 4 tables (titles, daily_metrics, daily_prices, ingest_runs)
- **Next.js**: App Router, lightweight-charts, Tailwind CSS
- **Docker**: Postgres (required), ClickHouse (optional, commented out)

## Common Commands

```bash
make db-up          # Start Postgres
make migrate        # Run schema migration
make sync-titles    # Sync registry to DB
make worker         # Generate synthetic data for today
make ingest SOURCE=reddit DATE=2026-03-02  # Ingest from source
make prices START=2026-02-01 END=2026-03-02  # Compute prices
make dev-api        # Start API on :8000
make dev-web        # Start frontend on :3000
make test           # Run all tests (68 tests)
```
