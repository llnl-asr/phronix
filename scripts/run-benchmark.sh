#!/bin/bash
# Run the SWE-bench comparison: a baseline agent against the same agent with
# phronix, on identical tasks in identical containers.
#
#   run-benchmark.sh                          # claude, 6 tasks, fresh
#   run-benchmark.sh --harness opencode       # the other harness
#   run-benchmark.sh --tasks pilot-1.txt      # one task, to measure cost first
#   run-benchmark.sh --reuse                  # let it use earlier research
#   run-benchmark.sh --carry-root DIR         # a store of its own, for a clean pair
#
# See scripts/README.md for what the options mean and how to read the result.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
BENCH=/p/lustre5/haridev/phronix-bench
VENV=$BENCH/venv
SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

HARNESS=claude
TASKS=$BENCH/fast-6.txt
NODE=""
MODEL=""
TAG=""
TRIES=3
TIMEOUT=1800
FRESHNESS="--fresh"
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --harness) HARNESS="$2"; shift 2;;
    --tasks)   TASKS="$2";   shift 2;;
    --node)    NODE="$2";    shift 2;;
    --model)   MODEL="$2";   shift 2;;
    --tag)     TAG="$2";     shift 2;;
    --tries)   TRIES="$2";   shift 2;;
    --timeout) TIMEOUT="$2"; shift 2;;
    --carry-root) EXTRA+=(--carry-root "$2"); shift 2;;
    --fresh)   FRESHNESS="--fresh"; shift;;
    --reuse)   FRESHNESS="";        shift;;
    --research-on-retry) EXTRA+=(--research-on-retry); shift;;
    --limit)   EXTRA+=(--limit "$2"); shift 2;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2;;
  esac
done

case "$HARNESS" in
  claude)   ARMS="claude-bare,claude-phronix";     MODEL=${MODEL:-claude-sonnet-5}
            PROVIDER=anthropic;;
  opencode) ARMS="opencode-bare,opencode-phronix"; MODEL=${MODEL:-claude-sonnet-4.5}
            PROVIDER=livai;;
  *) echo "harness must be 'claude' or 'opencode', not '$HARNESS'" >&2; exit 2;;
esac
TAG=${TAG:-$HARNESS}

# Tasks may be named relative to the bench directory.
[ -f "$TASKS" ] || TASKS="$BENCH/$TASKS"
[ -f "$TASKS" ] || { echo "no such task file: $TASKS" >&2; exit 2; }

# The node runs the containers. Default to whatever allocation is live: the
# agent runs here, but podman must run on the compute node.
if [ -z "$NODE" ]; then
  NODE=$(flux jobs -a --no-header 2>/dev/null | awk '$5=="R"{print $NF; exit}')
fi
[ -n "$NODE" ] || { echo "no running flux allocation; pass --node" >&2; exit 2; }

# Stop anything already running. Two runners writing one results file produce a
# file that looks complete and is not.
"$SCRIPTS/kill.sh" >/dev/null 2>&1
rm -f "$BENCH/runs/.runner.lock"

OUT=$BENCH/runs/$TAG-$(date +%m%d-%H%M%S)
echo "$OUT" > "$BENCH/CURRENT"

cd "$PROJECT" || exit 1
set -a; . "$PROJECT/.env" >/dev/null 2>&1; set +a

echo "harness : $HARNESS ($ARMS)"
echo "model   : $MODEL"
echo "tasks   : $TASKS ($(grep -c . "$TASKS") task(s))"
echo "node    : $NODE"
echo "mode    : ${FRESHNESS:---reuse} ${EXTRA[*]:-}"
echo "out     : $OUT"

nohup "$VENV/bin/python" -u -m tests.benchmark.cli run \
  --tasks "$TASKS" \
  --arms "$ARMS" \
  --model "$MODEL" --provider "$PROVIDER" \
  --node "$NODE" \
  --max-tries "$TRIES" --timeout "$TIMEOUT" \
  --until-pass --stall-limit 2 \
  --parallel-arms --force \
  $FRESHNESS "${EXTRA[@]}" \
  --out "$OUT" > "$OUT.log" 2>&1 &

RUNPID=$!
echo "pid     : $RUNPID"

# Record where this run lives, so it can be found later from anywhere.
#
# The process table is node-local: a run launched on the login node is invisible
# from a compute node, so `pgrep` reports "not running" for a perfectly healthy
# run — and, worse, for a runaway one that is still spending. This record
# survives the allocation the run was started in.
LOGS=$PROJECT/logs
mkdir -p "$LOGS"
cat > "$LOGS/$(basename "$OUT").json" <<JSON
{
  "pid": $RUNPID,
  "host": "$(hostname)",
  "run": "$OUT",
  "node": "$NODE",
  "harness": "$HARNESS",
  "arms": "$ARMS",
  "tasks": "$TASKS",
  "started": "$(date '+%F %T')"
}
JSON

echo
echo "watch:  $SCRIPTS/status.sh"
echo "spend:  $SCRIPTS/running.sh"
echo "stop:   $SCRIPTS/kill.sh"
