#!/bin/bash
# Run the SWE-bench comparison: a baseline agent against the same agent with
# phronix, on identical tasks in identical containers.
#
#   run-benchmark.sh                          # claude, 6 tasks, fresh
#   run-benchmark.sh --harness opencode       # the other harness
#   run-benchmark.sh --tasks pilot-1.txt      # one task, to measure cost first
#   run-benchmark.sh --phronix-only           # skip the baseline while iterating
#   run-benchmark.sh --parallel-tasks 6       # all six at once; invalidates reuse figures
#   run-benchmark.sh --serial-arms            # one arm at a time; REQUIRED when the
#                                             # endpoint is a single local server, or
#                                             # the arms queue behind each other and
#                                             # every timing is contention, not work
#   run-benchmark.sh --reuse                  # let it use earlier research
#   run-benchmark.sh --carry-root DIR         # a store of its own, for a clean pair
#   run-benchmark.sh --cluster tuolumne-llm/cluster.json   # the local GPU cluster:
#                                             # endpoint, model, key and provider all
#                                             # come from the cluster's own config
#   run-benchmark.sh --harness opencode --provider matrix33 \
#     --model nemotron-3.5 --base-url http://matrix33-pub.llnl.gov:8050/v1
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
NODES=""
TASKS_PER_NODE=""
MODEL=""
BASE_URL=""
CLUSTER=""
CLUSTER_DIRECT=""
ARMS_MODE="--parallel-arms"
TAG=""
ARMS_OVERRIDE=""
PROVIDER_OVERRIDE=""
PHRONIX_ONLY=""
TRIES=3
TIMEOUT=1800
FRESHNESS="--fresh"
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --harness) HARNESS="$2"; shift 2;;
    --arms)    ARMS_OVERRIDE="$2"; shift 2;;
    --provider) PROVIDER_OVERRIDE="$2"; shift 2;;
    --phronix-only) PHRONIX_ONLY=1; shift;;
    --tasks)   TASKS="$2";   shift 2;;
    --node)    NODE="$2";    shift 2;;
    --nodes)   NODES="$2";   shift 2;;
    --tasks-per-node) TASKS_PER_NODE="$2"; shift 2;;
    --model)   MODEL="$2";   shift 2;;
    --base-url) BASE_URL="$2"; shift 2;;
    --cluster) CLUSTER="${2:-}"; shift 2;;
    --no-kill) NO_KILL=1; shift;;
    --cluster-direct) CLUSTER_DIRECT=1; shift;;
    --serial-arms) ARMS_MODE=""; shift;;
    --tag)     TAG="$2";     shift 2;;
    --tries)   TRIES="$2";   shift 2;;
    --timeout) TIMEOUT="$2"; shift 2;;
    --carry-root) EXTRA+=(--carry-root "$2"); shift 2;;
    --fresh)   FRESHNESS="--fresh"; shift;;
    --reuse)   FRESHNESS="";        shift;;
    --research-on-retry) EXTRA+=(--research-on-retry); shift;;
    --parallel-tasks) PARALLEL_TASKS="$2"; EXTRA+=(--parallel-tasks "$2"); shift 2;;
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
# One arm, when the baseline is not the question.
#
# The comparison needs both, but iterating on phronix does not: the bare arm is
# roughly half the spend and none of the signal while the pipeline is being
# changed under it.
[ -n "$PROVIDER_OVERRIDE" ] && PROVIDER="$PROVIDER_OVERRIDE"
[ -n "$PHRONIX_ONLY" ] && ARMS="$HARNESS-phronix"
[ -n "$ARMS_OVERRIDE" ] && ARMS="$ARMS_OVERRIDE"
TAG=${TAG:-$HARNESS}

# Tasks may be named relative to the bench directory.
[ -f "$TASKS" ] || TASKS="$BENCH/$TASKS"
[ -f "$TASKS" ] || { echo "no such task file: $TASKS" >&2; exit 2; }

# The node runs the containers. Default to whatever allocation is live: the
# agent runs here, but podman must run on the compute node.
# An explicit --nodes wins over the guess. Checked FIRST: the flux fallback
# returns the allocation's whole hostlist as one bracket expression
# ("tuolumne[1171,1183,...]"), which is not a host anything can ssh to, and it
# was overriding a --nodes that named a real one.
if [ -z "$NODE" ] && [ -n "$NODES" ]; then
  # The first of the list is where single-node work goes; tasks are spread
  # across all of them.
  NODE=${NODES%%,*}
fi
if [ -z "$NODE" ]; then
  NODE=$(flux jobs -a --no-header 2>/dev/null | awk '$5=="R"{print $NF; exit}')
  # A hostlist is not a host. Expand it and take the first.
  case "$NODE" in
    *\[*) NODE=$(flux hostlist -e "$NODE" 2>/dev/null | awk '{print $1}') ;;
  esac
fi
[ -n "$NODE" ] || { echo "no running flux allocation; pass --node or --nodes" >&2; exit 2; }

# Stop anything already running. Two runners writing one results file produce a
# file that looks complete and is not.
#
# `--no-kill` is for the case where that reasoning does not apply: two runs on
# DIFFERENT harnesses write different files and can share a node. Measured the
# hard way — a second benchmark launched with the caller's own teardown skipped
# still died here, because this kill is a separate one and matches on the run
# path, so it stopped an unrelated run that was twenty minutes in.
if [ -z "${NO_KILL:-}" ]; then
  "$SCRIPTS/kill.sh" >/dev/null 2>&1
  rm -f "$BENCH/runs/.runner.lock"
fi

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

# Packing, when tasks run concurrently.
#
# Each task's research fans out — aspects, tuners, evaluators — so the agents in
# flight are tasks x fan-out, and that product is what starves an endpoint
# rather than the task count. Measured at 192 concurrent agents: every worker
# started, dozens hit a usage limit, most of the rest found no MCP server, and
# none did any work. So the per-task fan-out is divided by the number of tasks
# sharing the node.
if [ -n "${PARALLEL_TASKS:-}" ] && [ "${PARALLEL_TASKS:-1}" -gt 1 ]; then
  PER_TASK=$(( 24 / PARALLEL_TASKS ))
  [ "$PER_TASK" -lt 2 ] && PER_TASK=2
  export PHRONIX_BENCH_ASPECTS=$PER_TASK
  echo "packing : $PARALLEL_TASKS task(s) x $PER_TASK agent(s) each"
fi

nohup "$VENV/bin/python" -u -m tests.benchmark.cli run \
  --tasks "$TASKS" \
  --arms "$ARMS" \
  --model "$MODEL" --provider "$PROVIDER" \
  ${BASE_URL:+--base-url "$BASE_URL"} \
  ${NODES:+--nodes "$NODES"} \
  ${TASKS_PER_NODE:+--tasks-per-node "$TASKS_PER_NODE"} \
  ${CLUSTER:+--cluster "$CLUSTER"} \
  ${CLUSTER_DIRECT:+--cluster-direct} \
  --node "$NODE" \
  --max-tries "$TRIES" --timeout "$TIMEOUT" \
  --until-pass --stall-limit 2 \
  ${ARMS_MODE} --force \
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
