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

SUBMIT=""; NODES=8; WALL=""; QUEUE=pbatch; PAIR=""; CARRY_NAME=""; CAP=""
PASS_THROUGH=(); CARRY_FROM=""
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
    # How long this batch may SPEND, enforced by the script itself.
    #
    # Not the same thing as `-t`, and the difference is the point. `-t` is the
    # allocation: when it expires Flux kills the broker mid-write, and what the
    # run had learned in its last task is lost along with any record of which
    # tasks never came back. The cap is checked between passes, so the script
    # stops on its own terms with time in hand to checkpoint and finalise.
    --cap)      CAP="$2"; shift 2;;
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
    # Seed this run's carry root from a FINISHED run's own store.
    #
    # Every model in a sweep promotes into the same place unless told
    # otherwise, so by the third model the corpus is three models' work and a
    # "reuse" run measures transfer rather than that model's own learning.
    # Pointing at the fresh run's store is what makes the pair a pair.
    --carry-from) CARRY_FROM="$2"; shift 2;;
    # Fresh then reuse, one allocation, in that order.
    --pair)     PAIR=1; shift;;
    # Do not start until JOBID has finished, however it finished.
    --after)    AFTER="$2"; shift 2;;
    # Anything else goes THROUGH to run-group.sh, which passes it on to the
    # runner. `--harness opencode --provider livai` is the shape that needs
    # this: a site-gateway run is neither a local fleet nor the Claude
    # subscription, and enumerating every such flag here would mean editing
    # three scripts to add one option to the runner.
    *) PASS_THROUGH+=("$1"); shift;;
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
# ...but only for the SUBSCRIPTION, which is what has a window.
#
# A site gateway is hosted too and has its own key and its own capacity; it
# has no five-hour allowance to exhaust. Capping it to 4 would make a 30-task
# run crawl for a reason that does not apply to it. The subscription is the
# case with no `--provider`, since that is what "hosted Claude on this
# account" means here.
GATEWAY=""
for arg in "${PASS_THROUGH[@]}"; do
    [ "$arg" = "--provider" ] && GATEWAY=1
done
if [ -n "$HOSTED" ] && [ -z "$GATEWAY" ] \
   && [ "$PARALLEL" -gt "${HOSTED_PARALLEL_CAP:-4}" ]; then
    echo "hosted run: capping --parallel $PARALLEL to ${HOSTED_PARALLEL_CAP:-4}"          "(the account's allowance, not the nodes, is the limit here)"
    PARALLEL=${HOSTED_PARALLEL_CAP:-4}
fi

# Exported rather than passed: `run-group.sh` is invoked in several places
# here, and a flag added to one of them and not the others is the shape of
# bug that leaves half a sweep sharing a store.
[ -n "$CARRY_NAME" ] && export PHRONIX_CARRY="$PBENCH/carry-$CARRY_NAME"

# Seeded HERE, inside the job, so the source run has finished by the time it
# is read — a copy taken at submission would catch the fresh half mid-flight.
if [ -n "$CARRY_FROM" ] && [ -n "$CARRY_NAME" ]; then
    dest=$PBENCH/carry-$CARRY_NAME/.phronix
    rm -rf "$dest"; mkdir -p "$(dirname "$dest")"
    for store in "$CARRY_FROM"/*/store/.phronix; do
        [ -d "$store" ] || continue
        mkdir -p "$dest"
        cp -r "$store"/. "$dest"/ 2>/dev/null
    done
    say "carry seeded from $CARRY_FROM: $(ls -d "$dest"/capabilities/skills/*/ 2>/dev/null | wc -l) skill(s)"
fi

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
                 ${CAP:+--cap "$CAP"} \
                 ${CARRY_NAME:+--carry "$CARRY_NAME"} \
                 ${CARRY_FROM:+--carry-from "$CARRY_FROM"} \
                 "${PASS_THROUGH[@]}" \
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
#: Set when a pass could not start a run at all (see the manifest check in
#: the pass loop). Reported at the end so the job's exit status says so.
FAILED_LAUNCH=0

#: How many task-arms the previous pass left unfinished, so a pass that frees
#: none can be told from one that is still making headway.
prev_left=-1

#: Set when the pass loop stopped because the batch ran out of its own budget.
CAPPED=0

#: Where `finalize-run.py` promotes what a stopped run had learned.
CARRY_STORE_FOR_FINALIZE=${PHRONIX_CARRY:-/p/lustre3/haridev/phronix-bench/carry}/.phronix

seconds_of() {   # 90 | 90s | 30m | 2h | 1.5h | 1d -> seconds
    # Through awk, not bash arithmetic, because the wall time is not always a
    # whole number. `-t 2.5h` is a reasonable thing to ask for -- a run takes
    # under two hours, so six was three times too much -- and bash has no
    # floats, so `$(( 2.5 * 3600 ))` is a syntax error that leaves the limit
    # EMPTY. Every later `[ "$limit" -gt ... ]` then failed with "integer
    # expression expected" and the supervisor lost its wall guard entirely.
    local v=$1 unit mult
    case "$v" in
      *d) unit=${v%d}; mult=86400;;
      *h) unit=${v%h}; mult=3600;;
      *m) unit=${v%m}; mult=60;;
      *s) unit=${v%s}; mult=1;;
      *)  unit=$v;     mult=60;;     # bare number: flux reads it as minutes
    esac
    case "$unit" in
      ''|*[!0-9.]*|*.*.*) echo 0; return;;
    esac
    awk -v u="$unit" -v m="$mult" 'BEGIN { printf "%d\n", u * m }'
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
# ---- tidy up, and leave a note ---------------------------------------------
#
# On EXIT, however the job ends.
#
# This used to run only after the pass loop returned, so a cancelled job was
# killed before reaching it: the gpt-5.4-mini run finished all 60 task-arms
# and its numbers had to be recovered from `top.sh` by hand afterwards. A run
# that completes and leaves no record of itself is the expensive half of the
# work thrown away for the cheap half.
#
# Guarded against running twice: the trap fires on a normal exit as well.
_NOTE_WRITTEN=""
leave_a_note() {
    [ -n "$_NOTE_WRITTEN" ] && return 0
    _NOTE_WRITTEN=1
    "$PROJECT/scripts/kill.sh" >/dev/null 2>&1
    [ -z "$HOSTED" ] && "$LLM_DIR/stop.sh" >/dev/null 2>&1
    if [ -n "$out" ] && [ -d "$out" ]; then
        {
          top=$(cd "$PROJECT" && scripts/top.sh "$out" --once 2>/dev/null)
          # The TOTAL line, and each ARM's line beside it.
          #
          # A combined total hides the only comparison the run exists to make:
          # measured on a 30-task livai run, TOTAL read 21 pass / 39 fail while
          # the arms were 7/30 for bare and 14/30 for phronix — twice the pass
          # rate, invisible in the number that got written down.
          summary=$(printf '%s\n' "$top" | sed -n 2p | sed 's/^ *//' | cut -c1-150)
          arms=$(printf '%s\n' "$top" | grep -E "^v (claude|opencode)-" |
                 sed 's/^v //' | sed 's/  */ /g' | cut -c1-110)
          # The MODEL, read from top's own header rather than from $MODEL, which
          # is the batch's key ("gptoss120") and not what the run recorded.
          model=$(printf '%s\n' "$top" | sed -n 1p |
                  sed -E 's/.*[0-9]+[hms] +([^ ].*)$/\1/' |
                  sed -E 's/ +(fresh|reuse).*$//' | cut -c1-60)
          # Where skills actually live. This read `capabilities/tasks/`, the
          # pre-flattening path, and so reported "skills written: 0" for a run
          # whose store held sixteen.
          skills=$(ls -d "$out"/*/store/.phronix/capabilities/skills/*/ 2>/dev/null | wc -l)
          used=$(grep -rh "skill-use" "$out"/*/trace.log 2>/dev/null | grep -c "loaded \`")
          echo ""
          echo "### $NAME — \`$(basename "$out")\`  ($SIZE task(s), $count node(s))"
          echo ""
          echo "- model: \`${model:-unknown}\`"
          echo ""
          echo '```'
          echo "$summary"
          printf '%s\n' "$arms"
          echo '```'
          echo ""
          echo "- run: \`$out\`"
          echo "- fleet: \`$dlog\` (${ready})"
          echo "- skills written: **$skills**   attempts that loaded one: **$used**"
          echo "- \`scripts/top.sh $out --once\`"
        } >> "$PROJECT/$NOTES"
    fi
    # Checkpoint the learning and write down what never came back.
    #
    # Runs whether the pass loop ended at the cap, on a stuck tail, or
    # normally: a run that stopped for ANY reason with task-arms outstanding
    # should say so in its own results rather than leave them missing for a
    # reader to misinterpret as a smaller task list.
    if [ -n "${out:-}" ] && [ -f "$out/manifest.json" ]; then
        reason="stopped with work outstanding"
        [ "${CAPPED:-0}" = 1 ] && reason="reached the ${CAP} run cap"
        python3 "$PROJECT/scripts/finalize-run.py" "$out" \
            --carry "$CARRY_STORE_FOR_FINALIZE" --reason "$reason" 2>&1 |
            while read -r line; do say "$line"; done
    fi

    if [ "${FAILED_LAUNCH:-0}" = 1 ]; then
        # Said plainly and carried into the exit status. A batch that never
        # started a run must not read as a completion -- in the notes, in the
        # job state, or to whatever is watching the queue.
        say "batch $NAME FAILED: no run was produced"
        return 1
    fi
    say "batch $NAME done"
}
# Armed HERE, before the pass loop.
#
# A trap registered after the work is a trap that never runs when the
# work is what got killed: the gpt-5.4-mini job was cancelled mid-loop
# and its finished numbers had to be recovered by hand.
trap leave_a_note EXIT INT TERM

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
            "${PASS_THROUGH[@]}" \
            --size "$SIZE" --nodes "$live" > "$rlog" 2>&1
    else
        "$PROJECT/scripts/run-group.sh" "$INDEX" "" --cluster "$CLUSTER_JSON" \
            --parallel "$PARALLEL" "${RESUME[@]}" ${REUSE:+--reuse} \
            "${PASS_THROUGH[@]}" \
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

    # Did the pass produce a RUN at all, before asking what it has left?
    #
    # `left` is parsed out of `top.sh`, and a run that never started has
    # nothing to parse -- so `left` came back 0 and the next line called it
    # finished. That is how a full filesystem was reported as success: the
    # runner died on `Disk quota exceeded` before writing its manifest, the
    # batch said "run finished" in the same second it said "pass 1 started",
    # and four jobs in a row landed in the notes as COMPLETED having measured
    # nothing. A missing manifest is the difference between "did the work and
    # has none left" and "never got as far as starting".
    if [ -z "${out:-}" ] || [ ! -f "$out/manifest.json" ]; then
        say "pass $pass produced no run (see $rlog) — FAILED, not finished"
        FAILED_LAUNCH=1
        break
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

    # Out of the budget this batch was given? Stop while there is still time
    # to close the run properly.
    cap_s=$(seconds_of "${CAP:-0}")
    if [ "${cap_s:-0}" -gt 0 ] &&
       [ $(( $(date +%s) - STARTED )) -ge "$cap_s" ]; then
        say "reached the ${CAP} cap with ${left} task-arm(s) unfinished; finalising"
        CAPPED=1
        break
    fi

    # A pass that freed nothing will not free anything next time either.
    #
    # The tail of a run is one or two task-arms that never come back --
    # measured today, `psf__requests-2317` sat in `research` while 5.4 and sol
    # each ended pass 1 with 7 and 11 outstanding and pass 2 with exactly the
    # same 7 and 11. Every further pass re-attempts the same wedged arms for
    # another twenty minutes and ends where it started, which is what walks a
    # run into its wall guard with 28 of 30 tasks long since decided.
    #
    # So progress, not attempts, is the budget: two consecutive passes that
    # leave the same number outstanding means those arms are stuck, and the
    # run stops and reports them as unfinished rather than paying for a third.
    if [ "${left:-0}" -eq "${prev_left:--1}" ]; then
        say "pass $pass freed nothing (still ${left}); those task-arm(s) are stuck — stopping"
        break
    fi
    prev_left=$left

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

leave_a_note
