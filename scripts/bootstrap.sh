#!/usr/bin/env bash
# HypeX bootstrap: setup env, install deps, run migrations, start dev.
# Idempotent, macOS-friendly.

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "[bootstrap] HypeX root: $ROOT"

# 1. Env
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[bootstrap] Created .env from .env.example"
else
  echo "[bootstrap] .env exists"
fi

# 2. Python deps (venv or uv)
if command -v uv &>/dev/null; then
  echo "[bootstrap] Using uv"
  uv sync
else
  echo "[bootstrap] Using pip/venv"
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  .venv/bin/pip install -e packages/core -q
  .venv/bin/pip install fastapi uvicorn "psycopg[binary]" pydantic -q
fi

# 3. Web deps
if [[ -d apps/web ]]; then
  (cd apps/web && npm install --silent)
  echo "[bootstrap] Web deps installed"
fi

# 4. Postgres (Docker)
if command -v docker &>/dev/null; then
  docker compose up -d postgres 2>/dev/null || true
  echo "[bootstrap] Postgres started (or already running)"
else
  echo "[bootstrap] Docker not found; ensure Postgres is running"
fi

# 5. Sync titles from registry
echo "[bootstrap] Syncing titles..."
if command -v uv &>/dev/null; then
  uv run python -m apps.worker.sync_titles 2>/dev/null || true
else
  .venv/bin/python -m apps.worker.sync_titles 2>/dev/null || true
fi

# 6. Run worker once to create schema + synthetic data
echo "[bootstrap] Running worker for today..."
DATE=$(date +%Y-%m-%d)
if command -v uv &>/dev/null; then
  uv run python -m apps.worker.run --date "$DATE" 2>/dev/null || true
else
  .venv/bin/python -m apps.worker.run --date "$DATE" 2>/dev/null || true
fi

echo ""
echo "[bootstrap] Done. Start dev with:"
echo "  make dev-api   # Terminal 1"
echo "  make dev-web   # Terminal 2"
echo "  Or: make dev   # (prints instructions)"
