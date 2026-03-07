.PHONY: dev test fmt db-up db-down worker sync-titles check-structure migrate ingest prices backfill

# Start Postgres
db-up:
	docker compose up -d postgres

db-down:
	docker compose down

# Sync registry to Postgres titles table
sync-titles:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.sync_titles) || \
	 (.venv/bin/python -m apps.worker.sync_titles) || \
	 python -m apps.worker.sync_titles

# Run worker for today (run from project root)
worker:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.run --date $$(date +%Y-%m-%d)) || \
	 (.venv/bin/python -m apps.worker.run --date $$(date +%Y-%m-%d)) || \
	 python -m apps.worker.run --date $$(date +%Y-%m-%d)

# Development: start API + Web (run in separate terminals or use a process manager)
dev:
	@echo "Run in separate terminals:"
	@echo "  make dev-api   # FastAPI on :8000"
	@echo "  make dev-web   # Next.js on :3000"
	@echo "  make db-up     # Start Postgres first"

dev-api:
	@(cd apps/api && (command -v uv >/dev/null 2>&1 && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 || ../../.venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000))

dev-web:
	cd apps/web && npm run dev

# Repo structure check (spec compliance)
check-structure:
	@./scripts/check-structure.sh

# Run all tests
test: check-structure
	@(command -v uv >/dev/null 2>&1 && uv run pytest packages/core/tests apps/worker/tests packages/sources/reddit/tests apps/api/tests -v) || \
	 .venv/bin/pytest packages/core/tests apps/worker/tests packages/sources/reddit/tests apps/api/tests -v
	cd apps/web && npm run build

# Run schema migration
migrate:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.migrate) || \
	 (.venv/bin/python -m apps.worker.migrate) || \
	 python -m apps.worker.migrate

# Ingest from source (usage: make ingest SOURCE=reddit DATE=2026-03-02)
ingest:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.ingest --source $(SOURCE) --date $(DATE)) || \
	 (.venv/bin/python -m apps.worker.ingest --source $(SOURCE) --date $(DATE)) || \
	 python -m apps.worker.ingest --source $(SOURCE) --date $(DATE)

# Compute prices (usage: make prices START=2026-02-01 END=2026-03-02)
prices:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.prices --start $(START) --end $(END)) || \
	 (.venv/bin/python -m apps.worker.prices --start $(START) --end $(END)) || \
	 python -m apps.worker.prices --start $(START) --end $(END)

# Backfill mock data (usage: make backfill DAYS=30)
backfill:
	@(command -v uv >/dev/null 2>&1 && uv run python -m apps.worker.backfill --days $(DAYS)) || \
	 (.venv/bin/python -m apps.worker.backfill --days $(DAYS)) || \
	 python -m apps.worker.backfill --days $(DAYS)

# Format code
fmt:
	@(command -v uv >/dev/null 2>&1 && uv run ruff format packages/core apps/api apps/worker) || true
	cd apps/web && npm run lint 2>/dev/null || true
