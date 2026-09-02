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

SUBMIT=""; NODES=8; WALL=""; QUEUE=pbatch; PAIR=""; CARRY_NAME=""
SIZE=30; INDEX=1; PARALLEL=30; MODEL=""; NAME=""; SOURCE_LIST=""; HOSTED=""; REUSE=""; AFTER=""
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
    # A task list other than the full 300, e.g. the coverage sample.
    --source)   SOURCE_LIST="$2"; shift 2;;
    # A HOSTED run: no fleet, the allocation is only for containers.
    --hosted)   HOSTED=1; shift;;
    # Let the run READ what earlier runs learned, instead of starting clean.
    --reuse)    REUSE=1; shift;;
    # Which knowledge store this run reads and writes. A sweep over models
    # gives each its own, or the later ones inherit the earlier ones' work.
    --carry)    CARRY_NAME="$2"; shift 2;;
    # Fresh then reuse, one allocation, in that order.
    --pair)     PAIR=1; shift;;
    # Do not start until JOBID has finished, however it finished.
    --after)    AFTER="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
NAME=${NAME:-bench-${SIZE}x${INDEX}}
# Kept because `--pair` renames per phase, and the second phase must not build
# its name from the first phase's name.
BASE_NAME=$NAME

# Per-cluster defaults. Read from the fleet's own env.sh rather than repeated
# here, so a cluster that changes its paths changes them in one place.
LLM_DIR=$PROJECT/$FLEET
# shellcheck disable=SC1090
# A HOSTED run is bounded by the ACCOUNT, not by the hardware.
#
# `run-group.sh` drops a subscription run to one task at a time for exactly
# this reason, and the guard only fires when nobody passed `--parallel` — which
# this script always does. So `--hosted --parallel 30` put 60 task-arms on the
# subscription at once, the five-hour allowance went in minutes, and every
# agent exited rc=1 reporting `Not logged in · Please run /login`. That message
# reads as an expired login and is actually an exhausted quota: the same
# command run by hand on the same node authenticates fine.
#
# Capped rather than forced to 1: thirty tasks one at a time does not finish in
# a working day either. Pass `--parallel` after `--hosted` to override.
if [ -n "$HOSTED" ] && [ "$PARALLEL" -gt "${HOSTED_PARALLEL_CAP:-4}" ]; then
    echo "hosted run: capping --parallel $PARALLEL to ${HOSTED_PARALLEL_CAP:-4}"          "(the account's allowance, not the nodes, is the limit here)"
    PARALLEL=${HOSTED_PARALLEL_CAP:-4}
fi

# Exported rather than passed: `run-group.sh` is invoked in several places
# here, and a flag added to one of them and not the others is the shape of
# bug that leaves half a sweep sharing a store.
[ -n "$CARRY_NAME" ] && export PHRONIX_CARRY="$PBENCH/carry-$CARRY_NAME"

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
# `run-group.sh` takes the task list from SOURCE. Exported rather than passed
# as a flag because that is the interface it already has.
[ -n "$SOURCE_LIST" ] && export SOURCE=$SOURCE_LIST
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
    # `afterany`, not `afterok`: a fresh run that ends badly still leaves the
    # skills it wrote, and the reuse run exists to read them. Waiting for
    # success would discard the case worth measuring — what a failed pass
    # taught the next one.
    job=$(flux batch -N "$NODES" -t "$WALL" -q "$QUEUE" --job-name="$NAME" \
            ${AFTER:+--dependency=afterany:$AFTER} \
            --output="$out" \
            "$0" --size "$SIZE" --index "$INDEX" --parallel "$PARALLEL" \
                 --model "$MODEL" --name "$NAME" --time "$WALL" \
                 --fleet "$FLEET" --fleet-nodes "$FLEET_NODES" \
                 ${SOURCE_LIST:+--source "$SOURCE_LIST"} \
                 ${HOSTED:+--hosted} ${REUSE:+--reuse} ${PAIR:+--pair} \
                 ${CARRY_NAME:+--carry "$CARRY_NAME"} \
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

# ---- fleet, unless this run is hosted ---------------------------------------
#
# A hosted run needs the allocation for evaluation CONTAINERS and nothing
# else: the model is somebody else's problem, so deploying a fleet would take
# minutes and every GPU to serve nothing.
if [ -n "$HOSTED" ]; then
    say "hosted run: no fleet; the allocation is for containers only"
    BENCH_NODES=$nodes
    ready="hosted"
    dlog="(none)"
else

total=$((FLEET_NODES * REPLICAS_PER_NODE))
# This job's OWN fleet directory, so concurrent jobs cannot overwrite each
# other's `cluster.json`. Named for the job rather than the clock: two jobs
# starting in the same second would collide on a timestamp.
export RUNDIR=$LLM_ROOT/logs/run-$NAME-$(date +%m%d-%H%M%S)
CLUSTER_JSON=$RUNDIR/cluster.json
dlog=$LLM_ROOT/logs/deploy-$NAME-$(date +%H%M%S).log
mkdir -p "$(dirname "$dlog")" "$RUNDIR"
say "deploying $MODEL across $FLEET_NODES node(s) -> $dlog"
say "fleet config: $CLUSTER_JSON"
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
fi   # end: not hosted

# ---- the run ----------------------------------------------------------------
rlog=$PBENCH/$NAME-launch.log

# Defined HERE, above its first use: bash resolves a function when it is
# CALLED, so the supervisor loop below would have found nothing.
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

# The run is SUPERVISED, not launched once.
#
# A node failure ends whatever is running on it. Flux kills the enclosing job
# when the node is gone outright, and nothing inside can catch that — but most
# of what takes a run down is smaller: a node that stops accepting containers,
# an ssh that will not connect, a runner that dies. Measured, one dead node
# cost 105 in-flight tasks AND the ~500 task-arms the job had already
# finished, because the resubmission started from nothing.
#
# So each pass runs on the nodes that are still answering, and `--resume auto`
# carries forward everything earlier passes finished. A pass that dies costs
# the tasks that were in flight during it, and nothing else.
ATTEMPTS=${ATTEMPTS:-4}

# `--pair` runs fresh and then reuse inside ONE allocation.
#
# Two jobs cannot do this honestly. The reuse half has to start from what the
# fresh half learned, so it must run after it — and a second job queues, which
# on a contended queue means the pair is hours apart on different nodes, or
# the second never runs at all. Measured: a chained reuse job sat in DEPEND
# until its fresh half's allocation expired, and a pair submitted separately
# was cancelled before the second half started, three times over.
#
# One allocation, two phases, the fleet deployed once and shared. The phases
# are ordered and not interchangeable: reuse reads what fresh promoted.
PHASES="fresh"
[ -n "$PAIR" ] && PHASES="fresh reuse"
[ -z "$PAIR" ] && [ -n "$REUSE" ] && PHASES="reuse"

for phase in $PHASES; do
if [ -n "$PAIR" ]; then
    say "=== phase: $phase ==="
    # The phase decides the flag; the batch-level --reuse does not apply when
    # pairing, or the fresh half would read what it is supposed to be without.
    if [ "$phase" = "reuse" ]; then REUSE=1; else REUSE=""; fi
    NAME="${BASE_NAME}-${phase}"
fi
pass=0
while [ "$pass" -lt "$ATTEMPTS" ]; do
    pass=$((pass + 1))

    # Only the nodes that answer, re-derived every pass: a node that died in
    # the last pass must not be handed tasks in this one.
    live=""
    for h in $(printf '%s' "$BENCH_NODES" | tr ',' ' '); do
        if timeout 20 ssh -n -o BatchMode=yes -o ConnectTimeout=8 "$h" true 2>/dev/null; then
            live="${live:+$live,}$h"
        else
            say "pass $pass: $h is not reachable; leaving it out"
        fi
    done
    if [ -z "$live" ]; then
        say "no usable nodes left; stopping"
        break
    fi

    say "pass $pass/$ATTEMPTS: size=$SIZE index=$INDEX parallel=$PARALLEL on $(printf '%s' "$live" | tr ',' '\n' | grep -c .) node(s)"
    # Resume only from pass 2 on, and only within THIS batch.
    #
    # Resume exists so a pass that lost a node does not pay again for the
    # tasks already measured. On pass 1 there is nothing of ours to continue,
    # and `auto` will happily continue somebody ELSE's unfinished run: a fresh
    # 5-task batch picked up a cancelled run's five rows, skipped every task,
    # and produced a report over results it had not measured. The trace held
    # one line.
    RESUME=()
    [ "$pass" -gt 1 ] && RESUME=(--resume auto)
    if [ -n "$HOSTED" ]; then
        "$PROJECT/scripts/run-group.sh" "$INDEX" "" --subscription \
            --parallel "$PARALLEL" "${RESUME[@]}" ${MODEL:+--model "$MODEL"} \
            ${REUSE:+--reuse} \
            --size "$SIZE" --nodes "$live" > "$rlog" 2>&1
    else
        "$PROJECT/scripts/run-group.sh" "$INDEX" "" --cluster "$CLUSTER_JSON" \
            --parallel "$PARALLEL" "${RESUME[@]}" ${REUSE:+--reuse} \
            --size "$SIZE" --nodes "$live" > "$rlog" 2>&1
    fi
    out=$(grep -E "^out " "$rlog" 2>/dev/null | awk '{print $3}')
    runner=$(grep -E "^pid " "$rlog" 2>/dev/null | awk '{print $3}')
    say "pass $pass started: ${out:-see $rlog} (runner ${runner:-unknown})"

    # WAIT for it. `run-group.sh` returns as soon as it has a pid, so its exit
    # means "started", not "finished".
    if [ -n "$runner" ]; then
        while kill -0 "$runner" 2>/dev/null; do sleep 60; done
    else
        sleep 60
        while pgrep -f "benchmark.cli run" >/dev/null 2>&1; do sleep 60; done
    fi

    # Did it get through the list? `top.sh --once` reports what is left; a run
    # with nothing running and nothing queued is done, however it ended.
    left=$("$PROJECT/scripts/top.sh" "${out:-}" --once 2>/dev/null |
           sed -n 2p | grep -oE "[0-9]+ run" | grep -oE "[0-9]+" || echo 0)
    if [ "${left:-0}" -eq 0 ]; then
        say "run finished: ${out:-see $rlog}"
        break
    fi
    say "pass $pass ended with ${left} task-arm(s) unfinished; resuming"

    # Out of wall clock is not a reason to start another pass.
    limit_s=$(seconds_of "$WALL")
    if [ "${limit_s:-0}" -gt 0 ] &&
       [ $(( STARTED + limit_s - 600 )) -lt "$(date +%s)" ]; then
        say "less than 10m of the allocation left; not starting another pass"
        break
    fi
done

# Out of wall clock is a reason to skip the REUSE half rather than start it
# with no room: a reuse phase cut off halfway measures nothing and the fresh
# half's result is still worth having.
limit_s=$(seconds_of "$WALL")
if [ -n "$PAIR" ] && [ "${limit_s:-0}" -gt 0 ] &&
   [ $(( STARTED + limit_s - 900 )) -lt "$(date +%s)" ]; then
    say "less than 15m left; stopping after the $phase phase"
    break
fi
done

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
# ...unless somebody else is waiting for the nodes.
#
# The hold is right for ONE run: it keeps the fleet and containers alive to be
# looked at, and time already granted cannot be got back. It is wrong the
# moment there is a queue. Measured: a 300-task run finished in 2h05m of its
# 24h and then sat on 64 idle nodes for the remaining 21h50m while two more
# jobs of the same batch waited in SCHED — the hold that exists to avoid
# wasting an allocation was wasting three.
#
# Only OUR jobs count. Cancelling ourselves because a stranger is queued would
# hand the nodes to the scheduler, not to the work this is part of.
queued=$(flux jobs -a --no-header -o "{name} {state}" 2>/dev/null |
         awk '$2=="SCHED" || $2=="DEPEND"' | grep -c "^tuo-\|^bench-\|^corona-" || true)
# How long a finished job keeps its nodes so the fleet and containers can be
# looked at in place. Not the whole wall: idle nodes help nobody, and the
# reason to over-ask for time is to be sure the run FINISHES, not to sit on
# the surplus. Measured, that surplus was 21h50m of 64 idle nodes.
HOLD_S=${HOLD_S:-1200}
if [ "${queued:-0}" -gt 0 ]; then
    say "$queued job(s) of this batch are waiting; releasing the nodes now"
    limit=0
else
    limit=$(seconds_of "$WALL")
    elapsed=$(( $(date +%s) - STARTED ))
    if [ "$limit" -gt $(( elapsed + HOLD_S )) ]; then
        say "run finished with $(( (limit - elapsed) / 60 ))m left; holding $(( HOLD_S / 60 ))m for inspection, then releasing"
        limit=$(( elapsed + HOLD_S ))
    fi
fi
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
[ -z "$HOSTED" ] && "$LLM_DIR/stop.sh" >/dev/null 2>&1
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
