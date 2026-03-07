#!/usr/bin/env bash
# Repo structure check: fail if spec violations.
# - packages/api and packages/web must NOT exist
# - docs/ and scripts/ must exist

set -e
cd "$(dirname "$0")/.."
ERR=0

if [[ -d packages/api ]]; then
  echo "ERROR: packages/api must not exist (API lives in apps/api)"
  ERR=1
fi

if [[ -d packages/web ]]; then
  echo "ERROR: packages/web must not exist (Web lives in apps/web)"
  ERR=1
fi

if [[ ! -d docs ]]; then
  echo "ERROR: docs/ is required"
  ERR=1
fi

if [[ ! -d scripts ]]; then
  echo "ERROR: scripts/ is required"
  ERR=1
fi

if [[ $ERR -eq 1 ]]; then
  exit 1
fi

echo "Repo structure OK"
