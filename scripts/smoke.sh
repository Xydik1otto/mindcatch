#!/usr/bin/env bash
# Smoke test: boots uvicorn on a random port with a throwaway SQLite DB and
# checks the main endpoints (curl + grep). Prints PASS/FAIL per check.
# Usage: bash scripts/smoke.sh   (works in git-bash / Linux / macOS)
set -u
cd "$(dirname "$0")/.."

PORT=$(( (RANDOM % 2000) + 18000 ))
SMOKE_TMP="$(python -c "import tempfile; print(tempfile.mkdtemp(prefix='mindcatch-smoke-'))")"
export MINDCATCH_DB="$SMOKE_TMP/smoke.db"
BASE="http://127.0.0.1:$PORT"

echo ">> booting uvicorn on :$PORT (db: $MINDCATCH_DB)"
python -m uvicorn app.main:app --port "$PORT" --log-level warning &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null; wait "$APP_PID" 2>/dev/null' EXIT

# wait for readiness (max ~15 s)
for _ in $(seq 1 30); do
  curl -sf "$BASE/api/ocr-status" >/dev/null 2>&1 && break
  sleep 0.5
done

fail=0
check() { # <name> <expected-substring> <curl-args...>
  local name="$1" want="$2"; shift 2
  local body
  body=$(curl -sf "$@") || { echo "FAIL $name (request failed)"; fail=1; return; }
  if printf '%s' "$body" | grep -q "$want"; then echo "PASS $name"
  else echo "FAIL $name (expected '$want')"; fail=1; fi
}

check "index serves UI"            "Mindcatch"        "$BASE/"
check "manifest"                   "Mindcatch"        "$BASE/manifest.json"
check "favicon"                    "<svg"             "$BASE/favicon.svg"
# NOTE: ASCII-only payloads/queries here — Windows curl.exe mangles non-ASCII
# argv (codepage), so UTF-8 parsing itself is covered by pytest, not smoke.
check "quick capture (date parse)" "reminder"         -X POST "$BASE/api/quick" \
  -H 'Content-Type: application/json' -d '{"text":"smoke task tomorrow 15:00"}'
check "items list"                 '"status"'         "$BASE/api/items"
check "digest"                     '"tasks"'          "$BASE/api/digest"
check "tags endpoint"              '\['               "$BASE/api/tags"
check "search"                     '"id"'             -G "$BASE/api/search" --data-urlencode "q=smoke"
check "archive"                    '\['               "$BASE/api/archive"
check "focus stats (svg)"          "<svg"             "$BASE/api/stats/focus"
check "weekly review"              '"week_start"'     "$BASE/api/review/weekly"
check "ocr status"                 "ocr_available"    "$BASE/api/ocr-status"

if [ "$fail" -eq 0 ]; then echo "SMOKE: PASS"; else echo "SMOKE: FAIL"; fi
exit "$fail"
