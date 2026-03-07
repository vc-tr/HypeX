#!/usr/bin/env bash
# HypeX lint: run formatters/linters for Python + web.
# Idempotent, macOS-friendly.

set -e
cd "$(dirname "$0")/.."

echo "[lint] Python..."
if command -v uv &>/dev/null; then
  uv run ruff format packages/core apps/api apps/worker 2>/dev/null || true
  uv run ruff check packages/core apps/api apps/worker 2>/dev/null || true
elif [[ -d .venv ]]; then
  .venv/bin/ruff format packages/core apps/api apps/worker 2>/dev/null || true
  .venv/bin/ruff check packages/core apps/api apps/worker 2>/dev/null || true
else
  echo "[lint] Skipping Python (no uv or .venv)"
fi

echo "[lint] Web..."
if [[ -d apps/web ]]; then
  (cd apps/web && npm run lint 2>/dev/null) || true
fi

echo "[lint] Done"
