# HypeX Data Model

Postgres tables used by the worker, ingestion pipeline, and API.

## `titles`

Canonical title registry (synced from `data/registry/` by the worker).

| Column         | Type   | Nullable | Description                    |
|----------------|--------|----------|--------------------------------|
| canonical_id   | TEXT   | NOT NULL | Primary key (slug)            |
| canonical_name | TEXT   | NOT NULL | Display name                  |
| medium         | TEXT   | NOT NULL | manga \| manhwa \| manhua \| webtoon |
| language       | TEXT   | NOT NULL | e.g. ja, ko, en               |
| aliases        | JSONB  |          | Array of alias strings, default `[]` |
| platform       | TEXT   |          | Optional platform             |
| year           | INT    |          | Optional year                 |
| created_at     | TIMESTAMPTZ |      | Set on insert                 |
| updated_at     | TIMESTAMPTZ |      | Set on insert/update         |

**Primary key:** `canonical_id`

## `daily_metrics`

Multi-metric daily data per title. Stores raw ingested signals (mentions, engagement, etc.).

| Column       | Type   | Nullable | Description                          |
|--------------|--------|----------|--------------------------------------|
| metric_date  | DATE   | NOT NULL | YYYY-MM-DD                           |
| canonical_id | TEXT   | NOT NULL | FK → titles                          |
| metric_name  | TEXT   | NOT NULL | e.g. mentions_count, engagement_score |
| value        | REAL   | NOT NULL | Metric value                         |
| confidence   | REAL   |          | 0.0–1.0, default 1.0                |
| raw_ref      | JSONB  |          | Source metadata (post IDs, etc.)     |

**Primary key:** `(metric_date, canonical_id, metric_name)`
**Foreign key:** `canonical_id` → `titles(canonical_id)` ON DELETE CASCADE
**Index:** `idx_daily_metrics_cid` on `canonical_id`

## `daily_prices`

Daily computed price (P_t) for paper trading; denormalized with hype_index.

| Column       | Type   | Nullable | Description        |
|--------------|--------|----------|--------------------|
| canonical_id | TEXT   | NOT NULL | FK → titles        |
| date         | DATE   | NOT NULL | YYYY-MM-DD         |
| hype_index   | REAL   | NOT NULL | Smoothed Hs_t      |
| price        | REAL   | NOT NULL | P_t                |

**Primary key:** `(canonical_id, date)`
**Foreign key:** `canonical_id` → `titles(canonical_id)` ON DELETE CASCADE

## `ingest_runs`

Tracks ingestion runs for idempotency and auditing.

| Column        | Type        | Nullable | Description                     |
|---------------|-------------|----------|---------------------------------|
| run_id        | TEXT        | NOT NULL | Primary key (UUID)              |
| source        | TEXT        | NOT NULL | e.g. reddit                     |
| run_date      | DATE        | NOT NULL | Date being ingested             |
| status        | TEXT        | NOT NULL | running, completed, or failed   |
| started_at    | TIMESTAMPTZ |          | Run start time                  |
| finished_at   | TIMESTAMPTZ |          | Run end time                    |
| rows_ingested | INT         |          | Number of metric rows written   |
| error_message | TEXT        |          | Error details if failed         |

**Primary key:** `run_id`
**Unique constraint:** `(source, run_date)` — prevents duplicate runs

## Schema Management

- **Initial creation:** `ensure_schema()` in `apps/worker/run.py` creates all tables on first run
- **Migration:** `apps/worker/migrate.py` handles one-time schema upgrades (e.g., daily_metrics v1 → v2)
- **CLI:** `make migrate` or `python -m apps.worker.migrate`

## Price Pipeline

Computed from `daily_metrics` → `daily_prices`:

1. Rolling z-score per metric (window=28, min=7), winsorized to [-3, 3]
2. H_t = 0.7 × z(mentions_count) + 0.3 × z(engagement_score)
3. Hs_t = 0.7 × H_t + 0.3 × Hs_{t-1} (exponential smoothing)
4. P_t = P_{t-1} × exp(0.02 × Hs_t), P_0 = 100
5. Missing metrics ⇒ z = 0
