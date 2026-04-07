#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRIGGER_DIR="$REPO_ROOT/.ops"
TRIGGER_FILE="$TRIGGER_DIR/railway-redeploy-trigger.txt"
README_FILE="$REPO_ROOT/README.md"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "$TRIGGER_DIR"
printf '%s\n' "$TIMESTAMP" > "$TRIGGER_FILE"

echo "Updated $TRIGGER_FILE with $TIMESTAMP"

if [[ "${UPDATE_README:-0}" == "1" ]]; then
  printf 'Railway Dockerfile redeploy trigger: %s\n' "$TIMESTAMP" >> "$README_FILE"
  echo "Appended redeploy marker to $README_FILE"
fi
