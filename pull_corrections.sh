#!/usr/bin/env bash
# Print new correction requests as JSON lines and mark them seen. Usage: ./pull_corrections.sh > corrections.jsonl
set -euo pipefail
cd "$(dirname "$0")"
q() { wrangler d1 execute stringhomes --remote --json --command "$1"; }
max="$(q "select coalesce(max(seq), 0) m from corrections where status = 'new'" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)[0]["results"][0]["m"])')"
q "select seq, listing_id, url, field, value, note, client_at, received_at, sender from corrections where status = 'new' and seq <= $max order by seq" \
  | python3 -I -c 'import json,sys; [print(json.dumps(r)) for r in json.load(sys.stdin)[0]["results"]]'
q "update corrections set status = 'seen' where status = 'new' and seq <= $max" >/dev/null
