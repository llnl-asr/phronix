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
    # A store of its own, inheriting nothing. The CLI has supported this all
    # along; the launcher parses with an allow-list, so a flag it does not name
    # is refused however well the CLI understands it.
    --no-carry) EXTRA+=(--no-carry); shift;;
    --fresh)   FRESHNESS="--fresh"; shift;;
    --reuse)   FRESHNESS="";        shift;;
    --research-on-retry) EXTRA+=(--research-on-retry); shift;;
    --parallel-tasks) PARALLEL_TASKS="$2"; EXTRA+=(--parallel-tasks "$2"); shift 2;;
    --limit)   EXTRA+=(--limit "$2"); shift 2;;
    # Every research idea attempted against the real tests, in parallel.
    #
    # The parser is an allow-list, so a flag the CLI understands is still
    # refused here unless it is named — which is how "unknown option:
    # --attempt-candidates" happened twice with the CLI supporting it all along.
    --attempt-candidates) EXTRA+=(--attempt-candidates "$2"); CANDIDATES="$2"; shift 2;;
    --max-spend) EXTRA+=(--max-spend "$2"); MAX_SPEND="$2"; shift 2;;
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
[ -n "${MAX_SPEND:-}" ] && echo "budget  : \$$MAX_SPEND ceiling (no new task starts past it)"
echo "model   : $MODEL"
# Comments excluded, the same way `read_task_file` excludes them. `grep -c .`
# counted the header of a group file as four tasks — a number that is read
# before committing a budget should not disagree with what will run.
echo "tasks   : $TASKS ($(grep -vc '^[[:space:]]*#' "$TASKS") task(s))"
echo "node    : $NODE"
echo "mode    : ${FRESHNESS:---reuse} ${EXTRA[*]:-}"
echo "out     : $OUT"

# Candidate racing stays OFF unless asked for.
#
# `--attempt-candidates N` enables it and `swe-agent-bench.sh` sets its own
# default; this script does not, so running it directly keeps the single-attempt
# path. The value is still read here because the packing arithmetic below has to
# count racers as agents competing for the same slots.
CANDIDATES=${CANDIDATES:-1}

# Packing: how many agents may be in flight, sized against the fleet.
#
# Each task's research fans out — aspects, tuners, evaluators — so the agents in
# flight are (tasks x arms x fan-out), and that product is what starves an
# endpoint rather than the task count. Measured at 192 concurrent agents: every
# worker started, dozens hit a usage limit, most of the rest found no MCP
# server, and none did any work.
#
# The unit of capacity is a SLOT, not a GPU and not a replica. A slot holds one
# conversation with a private prompt cache; under the `solo` profile there is
# one per GPU deliberately, because the cache is per slot and two agents sharing
# one evict each other into full prefill — 11.1s against 0.3s for a cached
# prefix. So the fleet can hold exactly `slots` agent conversations at once
# without any of them losing its cache, and that is the number to size to.
#
# Aim for roughly one in-flight agent per slot. Above that, agents queue: the
# queue costs nothing in cache terms (a waiting request evicts nothing) but
# every second spent deferred is charged against the WALL-CLOCK budget of the
# stage waiting on it, which is how a research pass gets killed at rc=-9 after
# 1241s having produced nothing. Below it, GPUs idle.
#
# The old formula was `24 / PARALLEL_TASKS`, a constant fixed against a
# starvation incident rather than against a fleet, and it ignored ARMS entirely:
# a 2-arm run at 6 tasks asked for 6x4 phronix agents plus 6 bare ones — 30
# conversations against 8 slots, a queue 16 deep, and 74% utilisation while a
# quarter of the fleet sat idle waiting on agent think time.
SLOTS=$(PYTHONWARNINGS=ignore "$BENCH/venv/bin/python" - "$CLUSTER" <<'EOF' 2>/dev/null || echo 0
import json, os, sys, glob
try:
    cfg = json.load(open(sys.argv[1]))
except Exception:
    print(0); raise SystemExit
per = int(cfg.get("slots_per_replica") or 1)
replicas = len(cfg.get("servers") or [])
if not replicas:
    # `cluster.json` is written when a deploy FINISHES and lists `servers` as
    # empty until then; the live membership is the per-GPU records each replica
    # drops as it comes up. Same source `status.sh` reads, so this sizes against
    # the fleet that is actually serving rather than the last one recorded.
    replicas = len(glob.glob(os.path.join(cfg.get("run_dir", ""), "nodes", "*.json")))
print(int(cfg.get("slots") or replicas * per))
EOF
)
ARM_COUNT=$(awk -F, '{print NF}' <<< "$ARMS")
[ -z "$ARM_COUNT" ] && ARM_COUNT=1
#: Fewest agents a researching task may fan out to before the run stops being a
#: fair test of the pipeline. Override to trade research breadth for fleet size.
MIN_FANOUT=${PHRONIX_MIN_FANOUT:-2}
SLOTS_PER_REPLICA=$(PYTHONWARNINGS=ignore "$BENCH/venv/bin/python" -c "
import json,sys
try: print(int(json.load(open(sys.argv[1])).get('slots_per_replica') or 1))
except Exception: print(1)
" "$CLUSTER" 2>/dev/null || echo 1)

if [ -n "${PARALLEL_TASKS:-}" ] && [ "${PARALLEL_TASKS:-1}" -gt 1 ]; then
  if [ "${SLOTS:-0}" -gt 0 ]; then
    # One agent per slot, shared out across every task in every arm.
    PER_TASK=$(( SLOTS / (PARALLEL_TASKS * ARM_COUNT) ))
    # Never below MIN_FANOUT. Research IS the fan-out — the plan plus scouts
    # looking for ideas at once — so a fleet too small to host it should be
    # reported as too small, not quietly turned into a run that measures a
    # crippled pipeline and reports it as the pipeline.
    [ "$PER_TASK" -lt "$MIN_FANOUT" ] && PER_TASK=$MIN_FANOUT
  else
    PER_TASK=$(( 24 / PARALLEL_TASKS ))          # no fleet record; old default
    [ "$PER_TASK" -lt 2 ] && PER_TASK=2
  fi
  export PHRONIX_BENCH_ASPECTS=$PER_TASK
  # Racers count too. They are agents like any other, they run concurrently
  # with each other, and leaving them out of the arithmetic understated demand
  # by a factor of the candidate count — which is exactly when the queue gets
  # deep enough to eat a stage's wall-clock budget.
  DEMAND=$(( PARALLEL_TASKS * ARM_COUNT * PER_TASK ))
  RACERS=$(( PARALLEL_TASKS * CANDIDATES ))
  echo "packing : $PARALLEL_TASKS task(s) x $ARM_COUNT arm(s) x $PER_TASK agent(s)" \
       "= $DEMAND researching, + $RACERS racer(s) vs ${SLOTS:-?} slot(s)"
  # Say it plainly when the run cannot fit, rather than letting it show up later
  # as research stages timing out for no visible reason. The message names the
  # fleet that WOULD fit, because "oversubscribed" without a number leaves the
  # reader to redo this arithmetic by hand.
  if [ "${SLOTS:-0}" -gt 0 ] && [ "$DEMAND" -gt "$SLOTS" ]; then
    NEED_GPU=$(( DEMAND / ${SLOTS_PER_REPLICA:-1} ))
    echo "warning : oversubscribed ${DEMAND}:${SLOTS} — agents will queue, and"
    echo "          queue time is charged against each stage's wall-clock budget."
    echo "          this shape needs ~${NEED_GPU} slot(s); either deploy that many,"
    echo "          or drop to --parallel-tasks $(( SLOTS / (ARM_COUNT * MIN_FANOUT) ))."
  fi
fi

# A fleet session, for the exact window this run occupies.
#
# Every llama-server counter is cumulative since that server booted, and the
# fleet is up before a run starts and stays up after it ends — so the lifetime
# figures include work that is not this run's, and there is otherwise no way to
# say what the GPUs did FOR IT. `session.sh start` marks the window and samples
# what has no counter to difference (requests in flight, prompt-cache reuse);
# the watcher below closes it when the run's process goes, whether it finished
# or was killed, and leaves the report in the run directory beside the results.
#
# Only for cluster runs: a hosted-endpoint run has no fleet to measure.
SESSION=""
if [ -n "$CLUSTER" ] && [ -x "$PROJECT/tuolumne-llm/session.sh" ]; then
  SESSION="bench-$(basename "$OUT")"
  if "$PROJECT/tuolumne-llm/session.sh" start "$SESSION" >/dev/null 2>&1; then
    echo "session : $SESSION (fleet stats for this run)"
  else
    SESSION=""
  fi
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

# Close the session when the run's process goes.
#
# This script returns as soon as the runner is launched — it does not wait for
# the run — so the close has to be somebody's job. `setsid` because that
# somebody must outlive this shell, and `kill -0` because the run may equally
# end by finishing or by `kill.sh`: both leave a session that would otherwise
# stay open and absorb the NEXT run's traffic into this one's window.
if [ -n "$SESSION" ]; then
  setsid bash -c '
    while kill -0 '"$RUNPID"' 2>/dev/null; do sleep 20; done
    "'"$PROJECT"'/tuolumne-llm/session.sh" stop "'"$SESSION"'" \
      > "'"$OUT"'/fleet-session.txt" 2>&1
  ' >/dev/null 2>&1 < /dev/null &
fi

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
[ -n "$SESSION" ] && echo "fleet:  $PROJECT/tuolumne-llm/session.sh report  (stats for this run's window)"
echo "watch:  $SCRIPTS/status.sh"
echo "spend:  $SCRIPTS/running.sh"
echo "stop:   $SCRIPTS/kill.sh"
