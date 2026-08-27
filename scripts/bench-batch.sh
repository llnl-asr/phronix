#!/bin/bash
# One batch job: bring up the fleet, run a slice of the task list, tidy up.
#
# Submitted, not run by hand:
#
#   scripts/bench-batch.sh --submit -N 32 -t 24h -q pbatch --size 300 --parallel 60
#   scripts/bench-batch.sh --submit -N 8  -t 60m -q pdebug --size 30 --index 4
#
# Without `--submit` it IS the payload, and expects to be inside the
# allocation — which is what `flux batch` gives it. Everything is co-located:
# the fleet takes every node, and the containers and agents run on those same
# nodes. On a 4-GPU node that is four llama-servers and a share of 96 cores,
# and the alternative is holding nodes back from the fleet to do work that is
# mostly waiting on the fleet.
#
# The whole cycle has to fit the wall limit: fleet load is ~5 minutes for
# gpt-oss-120b, and a task is ~20 minutes at three tries. `-t` is the ONE
# number that decides whether the tail completes or is cut off mid-attempt, so
# it is a required argument rather than a default that silently truncates.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
source "$PROJECT/scripts/bench-root.sh"
PBENCH=$(bench_root)

SUBMIT=""; NODES=8; WALL=""; QUEUE=pbatch
SIZE=30; INDEX=1; PARALLEL=30; MODEL=""; NAME=""
# Which cluster this batch is for. Everything that differs between them —
# the fleet directory, the log root, the default model, the per-node shape —
# hangs off this one variable, the same way `run-group.sh` already works.
FLEET=${PHRONIX_FLEET:-tuolumne-llm}
# How many of the allocation's nodes serve the MODEL. The rest run the agents
# and the evaluation containers.
#
# Tuolumne co-locates everything: a 4-GPU APU node has 96 cores and the agents
# are mostly waiting on the fleet, so holding nodes back from it would be
# waste. Corona cannot: four llama-servers there take 44 of 48 cores, and the
# agents now run on the compute nodes too, so a co-located node has four cores
# left for thirty agents. Measured on a 5+3 split — 20 replicas, agents on the
# other three — each agent got 13.5 tok/s against 7 when the fleet was smaller.
FLEET_NODES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --submit)   SUBMIT=1; shift;;
    -N|--nodes) NODES="$2"; shift 2;;
    -t|--time)  WALL="$2"; shift 2;;
    -q|--queue) QUEUE="$2"; shift 2;;
    --size)     SIZE="$2"; shift 2;;
    --index)    INDEX="$2"; shift 2;;
    --parallel) PARALLEL="$2"; shift 2;;
    --model)    MODEL="$2"; shift 2;;
    --name)     NAME="$2"; shift 2;;
    --fleet)    FLEET="$2"; shift 2;;
    --fleet-nodes) FLEET_NODES="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
NAME=${NAME:-bench-${SIZE}x${INDEX}}

# Per-cluster defaults. Read from the fleet's own env.sh rather than repeated
# here, so a cluster that changes its paths changes them in one place.
LLM_DIR=$PROJECT/$FLEET
# shellcheck disable=SC1090
LLM_ROOT=$(cd "$LLM_DIR" && bash -c 'source ./env.sh >/dev/null 2>&1; echo "$LLM_ROOT"')
case "$FLEET" in
  corona-llm)
      MODEL=${MODEL:-nemotron}
      # 2 GPUs per replica: at one GPU each, a replica sat at 94% of a 32 GB
      # card and two of sixteen died on the compute buffer. See interesting-corona.md.
      : "${GPUS_PER_NODE:=4}" "${GPUS_PER_SERVER:=2}" "${CORES_PER_SERVER:=11}"
      : "${LLAMA_SLOTS:=2}" "${LLAMA_UBATCH:=1024}" "${LLAMA_BATCH:=1024}"
      : "${LLAMA_CACHE_RAM:=16384}" "${LLAMA_THREADS:=10}"
      export GPUS_PER_NODE GPUS_PER_SERVER CORES_PER_SERVER LLAMA_SLOTS \
             LLAMA_UBATCH LLAMA_BATCH LLAMA_CACHE_RAM LLAMA_THREADS
      REPLICAS_PER_NODE=$GPUS_PER_NODE
      # Five of eight to the fleet: the split that was measured.
      DEFAULT_FLEET_NODES=$(( NODES * 5 / 8 ))
      [ "$DEFAULT_FLEET_NODES" -lt 1 ] && DEFAULT_FLEET_NODES=1
      ;;
  *)  MODEL=${MODEL:-gptoss120}
      REPLICAS_PER_NODE=4
      DEFAULT_FLEET_NODES=$NODES        # co-located, as it always was
      ;;
esac
FLEET_NODES=${FLEET_NODES:-$DEFAULT_FLEET_NODES}
export PHRONIX_FLEET=$FLEET
# Each cluster keeps its own notes: the numbers are not comparable
# across them (different GPUs, different model, different shape).
case "$FLEET" in
  corona-llm) NOTES=interesting-corona.md;;
  *)          NOTES=interesting.md;;
esac

if [ -n "$SUBMIT" ]; then
    [ -n "$WALL" ] || { echo "-t is required: it decides whether the tail finishes" >&2; exit 2; }
    out=$PBENCH/batch-$NAME-$(date +%m%d-%H%M%S).log
    # `flux batch` runs this same script INSIDE the allocation, with the same
    # arguments minus `--submit`. One file, so the thing submitted and the
    # thing that runs cannot drift apart.
    job=$(flux batch -N "$NODES" -t "$WALL" -q "$QUEUE" --job-name="$NAME" \
            --output="$out" \
            "$0" --size "$SIZE" --index "$INDEX" --parallel "$PARALLEL" \
                 --model "$MODEL" --name "$NAME" --time "$WALL" \
                 --fleet "$FLEET" --fleet-nodes "$FLEET_NODES" \
                 2>&1 | tr -d '[:space:]')
    case "$job" in
      f*) echo "submitted $job   ($NODES nodes, $WALL, $QUEUE)"
          echo "  log      : $out"
          echo "  progress : scripts/top.sh --once"
          echo "  cancel   : flux cancel $job"
          printf '%s\n' "$job" > "$PBENCH/last-batch-job.txt";;
      *)  echo "submission failed: $job" >&2; exit 1;;
    esac
    exit 0
fi

# ---------------------------------------------------------------- the payload
say() { echo "[$(date +%H:%M:%S)] $*"; }
STARTED=$(date +%s)
say "batch $NAME starting: size=$SIZE index=$INDEX parallel=$PARALLEL model=$MODEL"

# Inside the allocation, so no `flux proxy`: this process IS in it.
hosts=$(flux getattr hostlist 2>/dev/null | tail -1)
nodes=$("$PBENCH/venv/bin/python" - "$hosts" <<'PY'
import re, sys
text = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
m = re.match(r"^([A-Za-z][A-Za-z0-9-]*)\[(.*)\]$", text)
out = []
if m:
    stem, inner = m.group(1), m.group(2)
    for part in inner.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            out += [f"{stem}{n}" for n in range(int(lo), int(hi) + 1)]
        elif part:
            out.append(stem + part)
elif text:
    out = text.split()
print(",".join(out))
PY
)
count=$(printf '%s' "$nodes" | tr ',' '\n' | grep -c .)
say "nodes ($count): $nodes"
[ "$count" -gt 0 ] || { echo "no nodes; not in an allocation?" >&2; exit 1; }

# ---- split the allocation ---------------------------------------------------
#
# `deploy.sh` serves on a PREFIX of the allocation (NNODES), so the fleet takes
# the first N and the benchmark is told to use the rest. Co-located clusters
# set FLEET_NODES to the whole allocation and BENCH_NODES comes out empty,
# which is what `run-group.sh` already treats as "every node".
[ "$FLEET_NODES" -gt "$count" ] && FLEET_NODES=$count
FLEET_HOSTS=$(printf '%s' "$nodes" | cut -d, -f1-"$FLEET_NODES")
if [ "$FLEET_NODES" -lt "$count" ]; then
    BENCH_NODES=$(printf '%s' "$nodes" | cut -d, -f$((FLEET_NODES + 1))-)
else
    BENCH_NODES=$nodes
fi
say "fleet on $FLEET_NODES node(s): $FLEET_HOSTS"
say "bench on: $BENCH_NODES"

# ---- fleet ------------------------------------------------------------------
total=$((FLEET_NODES * REPLICAS_PER_NODE))
dlog=$LLM_ROOT/logs/deploy-$NAME-$(date +%H%M%S).log
mkdir -p "$(dirname "$dlog")"
say "deploying $MODEL across $FLEET_NODES node(s) -> $dlog"
NNODES=$FLEET_NODES "$LLM_DIR/deploy.sh" "$MODEL" > "$dlog" 2>&1 &
deploy=$!
# Wait for MOST of it, not all: one replica that never loads must not hold a
# 24-hour job at the starting line.
want=$(( total * 85 / 100 ))
for _ in $(seq 1 90); do
    n=$(grep -oE "[0-9]+/$total ready" "$dlog" 2>/dev/null | tail -1 | cut -d/ -f1)
    [ "${n:-0}" -ge "$want" ] 2>/dev/null && break
    kill -0 "$deploy" 2>/dev/null || break
    sleep 20
done
ready=$(grep -oE "[0-9]+/$total ready" "$dlog" 2>/dev/null | tail -1)
say "fleet ${ready:-unknown}"
up=${ready%%/*}
case "$up" in
  ''|*[!0-9]*) say "fleet never reported readiness; stopping"; exit 1;;
esac
if [ "$up" -lt 4 ]; then
    say "fleet too small ($ready); stopping rather than measuring a starved run"
    exit 1
fi

# ---- the run ----------------------------------------------------------------
rlog=$PBENCH/$NAME-launch.log
say "running: size=$SIZE index=$INDEX parallel=$PARALLEL"
"$PROJECT/scripts/run-group.sh" "$INDEX" "" --local --parallel "$PARALLEL" \
    --size "$SIZE" --nodes "$BENCH_NODES" > "$rlog" 2>&1
out=$(grep -E "^out " "$rlog" 2>/dev/null | awk '{print $3}')
runner=$(grep -E "^pid " "$rlog" 2>/dev/null | awk '{print $3}')
say "run started: ${out:-see $rlog} (runner ${runner:-unknown})"

# WAIT for it. `run-group.sh` launches the runner with `nohup ... &` and
# returns as soon as it has a pid, so its exit means "started", not
# "finished". Treating the two as the same thing made this script tear the
# fleet down eleven seconds after starting the run and report `batch done`:
#
#     [00:51:27] running: size=30 index=1 parallel=30
#     [00:51:38] run finished: .../claude-0827-005137
#     [00:52:17] batch group1 done
#
# The run directory never even survived the cleanup.
if [ -n "$runner" ]; then
    while kill -0 "$runner" 2>/dev/null; do sleep 60; done
else
    # No pid to wait on: fall back to watching for the runner process by name,
    # and give it a moment to appear before deciding it never started.
    sleep 60
    while pgrep -f "benchmark.cli run" >/dev/null 2>&1; do sleep 60; done
fi
say "run finished: ${out:-see $rlog}"

# Hold the allocation for the rest of its window.
#
# The job used to exit the moment the run did, which returns the nodes — and
# with them the fleet, the containers and any chance of looking at the run in
# place. It also means a run that ends early (or dies early) hands back time
# that was already granted and cannot be got again: pdebug is contended, and
# the next request queues behind everyone else.
#
# So the job sleeps out its own `-t`, less a margin to tidy up in. Anyone who
# wants the nodes back sooner cancels the job, which is one command and an
# explicit decision.
seconds_of() {   # 90 | 90s | 30m | 2h | 1d -> seconds
    case "$1" in
      *d) echo $(( ${1%d} * 86400 ));;
      *h) echo $(( ${1%h} * 3600 ));;
      *m) echo $(( ${1%m} * 60 ));;
      *s) echo $(( ${1%s} ));;
      ''|*[!0-9]*) echo 0;;
      *)  echo $(( $1 * 60 ));;      # bare number: flux reads it as minutes
    esac
}
limit=$(seconds_of "$WALL")
if [ "${limit:-0}" -gt 0 ]; then
    margin=120
    left=$(( STARTED + limit - margin - $(date +%s) ))
    if [ "$left" -gt 0 ]; then
        say "holding the allocation for its remaining $(( left / 60 ))m"
        sleep "$left"
    fi
fi

# ---- tidy up, and leave a note ---------------------------------------------
"$PROJECT/scripts/kill.sh" >/dev/null 2>&1
"$LLM_DIR/stop.sh" >/dev/null 2>&1
if [ -n "$out" ] && [ -d "$out" ]; then
    {
      summary=$(cd "$PROJECT" && scripts/top.sh "$out" --once 2>/dev/null |
                sed -n 2p | sed 's/^ *//' | cut -c1-150)
      skills=$(ls "$out"/claude-phronix/store/.phronix/capabilities/tasks/ 2>/dev/null | wc -l)
      used=$(grep -rh "skill-use" "$out"/*/tasks/*/trace.log 2>/dev/null | grep -c "loaded \`")
      echo ""
      echo "### $NAME — \`$(basename "$out")\`  ($SIZE task(s), $count node(s))"
      echo ""
      echo '```'
      echo "$summary"
      echo '```'
      echo ""
      echo "- run: \`$out\`"
      echo "- fleet: \`$dlog\` (${ready})"
      echo "- skills written: **$skills**   attempts that loaded one: **$used**"
      echo "- \`scripts/top.sh $out --once\`"
    } >> "$PROJECT/$NOTES"
fi
say "batch $NAME done"
