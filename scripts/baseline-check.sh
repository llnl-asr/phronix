#!/bin/bash
# Can these instances be judged at all? Runs every task's tests unpatched.
#
#   baseline-check.sh                                  # all 9 tasks
#   baseline-check.sh --tasks fast-6.txt               # a specific list
#   baseline-check.sh --node tuolumne1075 --no-cache   # measure fresh
#
# No agent and no tokens: one container per instance, tests only. See
# scripts/README.md for the three environment faults this exists to catch.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
BENCH=/p/lustre5/haridev/phronix-bench
TASKS=$BENCH/fast-9.txt
NODE=""
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --tasks) TASKS="$2"; shift 2;;
    --node)  NODE="$2";  shift 2;;
    --no-cache) EXTRA+=(--no-cache); shift;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) EXTRA+=("$1"); shift;;
  esac
done

[ -f "$TASKS" ] || TASKS="$BENCH/$TASKS"
[ -f "$TASKS" ] || { echo "no such task file: $TASKS" >&2; exit 2; }

# Any live allocation will do — this competes with nothing.
if [ -z "$NODE" ]; then
  NODE=$(flux jobs -a --no-header 2>/dev/null | awk '$5=="R"{print $NF; exit}')
fi
[ -n "$NODE" ] || { echo "no running flux allocation; pass --node" >&2; exit 2; }

cd "$PROJECT" || exit 1
set -a; . "$PROJECT/.env" >/dev/null 2>&1; set +a

exec "$BENCH/venv/bin/python" -u -m tests.benchmark.cli baseline \
  --tasks "$TASKS" --node "$NODE" "${EXTRA[@]}"
