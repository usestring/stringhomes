#!/usr/bin/env bash
# Publish a freshly built site. Usage: ./deploy.sh <dir holding index.html and transit.json>
set -euo pipefail
src="${1:?usage: ./deploy.sh <built site dir>}"
here="$(cd "$(dirname "$0")" && pwd)"
for f in index.html transit.json; do
  [[ -s "$src/$f" ]] || { echo "missing $src/$f" >&2; exit 1; }
  cp "$src/$f" "$here/public/$f"
done
cd "$here"
wrangler pages deploy public --project-name stringhomes --branch main --commit-dirty=true
