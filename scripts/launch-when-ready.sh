#!/bin/bash
# Wait for the model endpoint to accept requests, then launch the run.
#
# The LiVAI key is capped ("Budget has been exceeded ... Max budget: 500.0") and
# every request 429s. A run started in that state does not fail loudly — it
# produces attempt after attempt of "0 steps, 0 tok, agent produced no patch",
# which reads as an agent that ran and did nothing. So the run waits for a real
# 200 rather than being started hopefully.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
BENCH=/p/lustre5/haridev/phronix-bench
# Scripts live in the project; only DATA lives on the PFS.
SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

TASKS="${1:-$BENCH/fast-6.txt}"
NODE="${2:-tuolumne1767}"
TAG="${3:-keyed}"
INTERVAL="${4:-120}"     # seconds between probes
DEADLINE="${5:-86400}"   # give up after this long (default 24h)

set -a; . "$PROJECT/.env" >/dev/null 2>&1; set +a

LOG=$BENCH/launch-when-ready.log
started=$(date +%s)
echo "$(date '+%F %T') waiting for the model endpoint; probing every ${INTERVAL}s" >> "$LOG"

while true; do
  code=$(curl -sS -m 30 -o /tmp/$USER/ready-probe.json -w '%{http_code}' \
    -X POST "https://livai-api.llnl.gov/v1/chat/completions" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"claude-sonnet-4.5","max_tokens":4,"messages":[{"role":"user","content":"hi"}]}' \
    2>/dev/null)

  if [ "$code" = "200" ]; then
    echo "$(date '+%F %T') endpoint accepted a request — launching" >> "$LOG"
    "$SCRIPTS/run-benchmark.sh" --tasks "$TASKS" --node "$NODE" --tag "$TAG" >> "$LOG" 2>&1
    exit 0
  fi

  now=$(date +%s)
  if [ $(( now - started )) -ge "$DEADLINE" ]; then
    echo "$(date '+%F %T') gave up after ${DEADLINE}s; endpoint still returning $code" >> "$LOG"
    exit 1
  fi

  # Log only when the reason changes, so a day of waiting is a few lines.
  reason=$(head -c 120 "/tmp/$USER/ready-probe.json" 2>/dev/null | tr -d '\n')
  if [ "$reason" != "${last_reason:-}" ]; then
    echo "$(date '+%F %T') http $code: $reason" >> "$LOG"
    last_reason="$reason"
  fi
  sleep "$INTERVAL"
done
