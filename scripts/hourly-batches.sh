#!/bin/bash
# Run a long task list in hourly batches with a per-batch spend ceiling.
#
#   scripts/hourly-batches.sh --tasks lite-300.txt --spend 25 [--every 3600]
#
# Why batches rather than one long run. A single 305-task run bills until it
# finishes or is killed: the only feedback is the invoice. Spending a fixed
# amount per hour turns that into a rate you can watch and stop, and it puts a
# natural inspection point between batches — the skills a batch wrote are on
# disk before the next one starts, which is when a bad pattern is cheapest to
# catch.
#
# Each batch continues where the last stopped. The runner's own `--max-spend`
# stops STARTING tasks past the ceiling, so a batch ends on a task boundary and
# whatever it did not reach is simply the next batch's list.
#
# Results are grouped at the end by `--group`, which reads every batch run
# directory and reports them as one.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
# `BENCH` collides with something in the login profile — it comes back
# as a session id, so paths built from it land in the wrong place.
PBENCH=/p/lustre5/haridev/phronix-bench
TASKS=""
SPEND=25
EVERY=3600
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --tasks)  TASKS="$2"; shift 2;;
    --spend)  SPEND="$2"; shift 2;;
    --every)  EVERY="$2"; shift 2;;
    --group)  GROUP_ONLY=1; shift;;
    *)        EXTRA+=("$1"); shift;;
  esac
done
[ -n "$TASKS" ] || { echo "need --tasks FILE"; exit 1; }
[ -f "$TASKS" ] || TASKS="$PBENCH/$TASKS"
[ -f "$TASKS" ] || { echo "no such task file: $TASKS"; exit 1; }

STAMP=$(date +%m%d-%H%M%S)
STATE=$PBENCH/batches/$STAMP
mkdir -p "$STATE"
REMAINING=$STATE/remaining.txt
grep -c . "$TASKS" > /dev/null
cp "$TASKS" "$REMAINING"
echo "batching $(grep -c . "$REMAINING") task(s), \$$SPEND every $((EVERY/60)) min"
echo "state: $STATE"

batch=0
while [ "$(grep -c . "$REMAINING")" -gt 0 ]; do
  batch=$((batch + 1))
  started=$(date +%s)
  left=$(grep -c . "$REMAINING")
  echo
  echo "=== batch $batch — $left task(s) left, ceiling \$$SPEND — $(date +%H:%M:%S)"

  "$PROJECT/scripts/run-benchmark.sh" --tasks "$REMAINING" \
      --max-spend "$SPEND" "${EXTRA[@]}" 2>&1 | tee "$STATE/batch-$batch.log" |
      grep -E "^(out|pid|packing|budget) " || true

  out=$(awk '/^out /{print $3}' "$STATE/batch-$batch.log" | tail -1)
  [ -n "$out" ] && echo "$out" >> "$STATE/runs.txt"

  # Wait for the batch to finish before deciding what is left: the launcher
  # returns as soon as the runner is detached.
  pid=$(awk '/^pid /{print $3}' "$STATE/batch-$batch.log" | tail -1)
  if [ -n "$pid" ]; then
    while kill -0 "$pid" 2>/dev/null; do sleep 20; done
  fi

  # What this batch actually finished, by instance id, from every arm's results.
  done_file=$STATE/done-$batch.txt
  : > "$done_file"
  if [ -n "$out" ]; then
    for r in "$out"/*/results.jsonl; do
      [ -f "$r" ] && "$PBENCH/venv/bin/python" -c "
import json,sys
for line in open(sys.argv[1]):
    try: print(json.loads(line).get('instance_id',''))
    except Exception: pass
" "$r" >> "$done_file"
    done
  fi
  sort -u "$done_file" -o "$done_file"
  finished=$(grep -c . "$done_file")
  echo "batch $batch finished $finished task(s)"

  if [ "$finished" -eq 0 ]; then
    echo "batch $batch completed no tasks — stopping rather than looping forever"
    break
  fi
  grep -vxF -f "$done_file" "$REMAINING" > "$REMAINING.next" || true
  mv "$REMAINING.next" "$REMAINING"

  [ "$(grep -c . "$REMAINING")" -gt 0 ] || break

  # Pace to the interval, measured from the batch's START so a slow batch does
  # not push every later one later. A batch that overran its hour starts the
  # next immediately rather than compounding the delay.
  elapsed=$(( $(date +%s) - started ))
  if [ "$elapsed" -lt "$EVERY" ]; then
    nap=$(( EVERY - elapsed ))
    echo "sleeping $((nap/60)) min until the next batch"
    sleep "$nap"
  fi
done

echo
echo "=== all batches done; grouping"
"$PROJECT/scripts/group-batches.sh" "$STATE"
