#!/usr/bin/env bash
# Print new correction requests as JSON lines and mark them seen. Usage: ./pull_corrections.sh > corrections.jsonl
set -euo pipefail
cd "$(dirname "$0")"
response_dir="$(mktemp -d /tmp/stringhomes-d1.XXXXXX)"
trap 'rm -f "$response_dir/response.json" "$response_dir/stderr"; rmdir "$response_dir"' EXIT
q() {
  local status=0
  wrangler d1 execute stringhomes --remote --json --command "$2" \
    > "$response_dir/response.json" 2> "$response_dir/stderr" || status=$?
  python3 -I parse_d1_response.py "$1" "$status" "$response_dir/response.json" "$response_dir/stderr"
}
max="$(q max "select coalesce(max(seq), 0) m from corrections where status = 'new'")"
q rows "select seq, listing_id, url, field, value, note, client_at, received_at, sender from corrections where status = 'new' and seq <= $max order by seq"
q check "update corrections set status = 'seen' where status = 'new' and seq <= $max"
