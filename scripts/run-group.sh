#!/bin/bash
# Run one group of the SWE-bench lite list inside a named Flux allocation.
#
#   scripts/run-group.sh 1 <alloc>                    # group 1 of 10, 30 tasks
#   scripts/run-group.sh 1 <alloc> --size 1           # group 1 of 300, one task
#   scripts/run-group.sh 4 <alloc> --size 50          # group 4 of 6, 50 tasks
#   scripts/run-group.sh 2 f3TkgpQVfpEb --spend 60    # a different ceiling
#   scripts/run-group.sh 3 f3TkgpQVfpEb --local       # the local GPU fleet
#   scripts/run-group.sh 1 <alloc> --subscription     # hosted Sonnet 5, one task
#                                                     # at a time, on the account
#   scripts/run-group.sh 1 <alloc> --research-first   # exercise the research
#                                                     # loop on EVERY task
#
# Ten groups of 30, from `lite-300.txt`. Hosted Claude Sonnet by default, five
# tasks at a time, with a $100 ceiling per group — enforced by the runner, which
# stops STARTING tasks past it, so the overrun is bounded by one task rather
# than by whatever was still queued.
#
# The allocation is for the evaluation CONTAINERS. A hosted run needs no GPUs;
# `--local` serves the model from the fleet in the same allocation, and then the
# container hosts are the allocation minus the nodes the fleet is on.
#
# Each group is INDEPENDENT: run in any order, on any allocation, and re-run one
# without disturbing the others. `--fresh --no-carry` gives every group its own
# store, so no group inherits another's learning.
#
# What that buys: a group can be run whenever an allocation is free, and a group
# that dies takes nothing with it. What it costs: cross-group reuse is not
# measured, because there is none — within a group the learning arm still
# benefits from its own earlier tasks, and that is the figure these runs report.
# Groups remain contiguous slices of lite-300.txt so a group is a fair sample of
# the list rather than a reordering of it.
#
# The allocation is for the evaluation CONTAINERS, not for a model: these runs
# use the Anthropic API, so no GPU fleet is involved and nodes buy container
# capacity only.
set -uo pipefail

PROJECT=/usr/WS2/haridev/phronix
# Which fleet directory to read cluster.json from. Two exist — tuolumne-llm/
# and corona-llm/ — and they are separate clusters with separate gateways, so
# a run has to name one. PHRONIX_FLEET=corona-llm switches every default here.
FLEET=${PHRONIX_FLEET:-tuolumne-llm}

# `BENCH` collides with something in the login profile — it comes back
# as a session id, so paths built from it land in the wrong place.
# The benchmark's own workspace: venv, task lists, run outputs. NOT the repo.
#
# Configurable because it is on a PARALLEL FILESYSTEM, and the two clusters do
# not share one — /p/lustre5 is Tuolumne's and is not mounted on corona, so a
# corona run needs its own root (/p/lustre3/haridev/phronix-bench) with its own
# venv and task lists. Unset, this is exactly the path it always was.
source "$PROJECT/scripts/bench-root.sh"
PBENCH=$(bench_root)
# NOT `GROUPS`: that is a bash builtin holding the user's group ids,
# and assigning to it is silently ignored — the path came out as the
# numeric gid, so every lookup missed.
GROUPDIR=$PBENCH/groups

INDEX=${1:-}
ALLOC=${2:-}
shift 2 2>/dev/null || true
[ -n "$INDEX" ] || { echo "usage: run-group.sh <index> <alloc-jobid> [options]"; exit 1; }

# Hosted Claude Sonnet, five tasks at a time.
#
# Five rather than thirty: the hosted model is the shared resource now, and a
# task's own turns are serialised anyway, so more concurrency buys wall-clock at
# the cost of every stage waiting on rate limits. Five also keeps a group inside
# a few hours and a sane bill.
#
# `--cluster FILE` switches to the local GPU fleet, where the dollar figure is
# notional and the ceiling is dropped.
SPEND=100
PARALLEL=5
SIZE=30
NODES=""
CLUSTER=""
SUBSCRIPTION=""
PARALLEL_SET=""
EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --spend)    SPEND="$2"; shift 2;;
    --parallel) PARALLEL="$2"; PARALLEL_SET=1; shift 2;;
    # Hosted Claude on the account's own subscription.
    #
    # One task at a time, because the constraint here is not dollars and not
    # GPUs but the account's usage allowance, and the way to keep that bounded
    # is to have one task's worth of agents in flight rather than five. Both
    # arms still run together, so a task is compared against its own baseline.
    #
    # The dollar figure stays on and stays useful, but read it as an ESTIMATE
    # OF API-EQUIVALENT USAGE rather than a bill: a subscription is not charged
    # per token, so the ceiling is a proxy for how much of the allowance a
    # group has eaten. Set `--spend 0` to remove it.
    --subscription) SUBSCRIPTION=1; shift;;
    --size)     SIZE="$2"; shift 2;;
    --nodes)    NODES="$2"; shift 2;;
    # Passed through rather than interpreted: the default is `auto`, which
    # measures the fleet, and a group has no better information than that.
    --pipeline) EXTRA+=(--pipeline "$2"); shift 2;;
    --resume)   EXTRA+=(--resume "$2"); shift 2;;
    --budget-scale) EXTRA+=(--budget-scale "$2"); shift 2;;
    --cluster)  CLUSTER="${2:-$PROJECT/$FLEET/cluster.json}"; shift 2;;
    --local)    CLUSTER=$PROJECT/$FLEET/cluster.json; shift;;
    *)          EXTRA+=("$1"); shift;;
  esac
done
# A local fleet bills nothing, so a dollar ceiling there would stop a run over a
# number that means nothing.
[ -n "$CLUSTER" ] && SPEND=0

# `--subscription` sets the shape unless the shape was asked for explicitly.
if [ -n "$SUBSCRIPTION" ]; then
  [ -n "$CLUSTER" ] && { echo "--subscription is a HOSTED run; drop --local/--cluster"; exit 2; }
  [ -z "$PARALLEL_SET" ] && PARALLEL=1
fi

# An allocation that is not RUNNING cannot host anything.
#
# `flux proxy` on a pending or finished job fails with "Unable to resolve <id>
# to a URI", which reads like a typo rather than an expired reservation — and by
# then the header has already printed as though the run were starting. Checked
# here so the message names the state and points at what is available.
if [ -n "$ALLOC" ]; then
  STATE=$(flux jobs -a --no-header 2>/dev/null | awk -v j="$ALLOC" '$1==j{print $5}')
  case "${STATE:-}" in
    R) ;;
    "") echo "no such allocation: $ALLOC"; flux jobs -a --no-header 2>/dev/null | head -5; exit 1;;
    *)  echo "allocation $ALLOC is not running (state $STATE)."
        echo
        echo "running allocations:"
        flux jobs -a --no-header 2>/dev/null | awk '$5=="R"{print "  " $1 "  " $6 " node(s)  " $8 " left"}'
        flux jobs -a --no-header 2>/dev/null | awk '$5=="R"' | grep -q . ||
            echo "  none — every allocation is pending or finished"
        echo
        echo "A HOSTED group needs nodes only for the evaluation containers;"
        echo "pass no allocation to run them here instead."
        exit 1;;
  esac
fi

# Sliced on demand from the master list, so `--size` can change between runs.
#
# Fixed group files meant the size was decided when they were generated:
# switching from 30 to 1 for a quick check meant regenerating all of them and
# renumbering, and a group already run no longer matched its own file. Slicing
# here makes `--size N` with index K mean exactly "the Kth block of N", and the
# slice is written under `groups/size-N/` so a run can still be traced to the
# exact list it used.
SOURCE=${SOURCE:-$PBENCH/lite-300.txt}
[ -f "$SOURCE" ] || { echo "no task list: $SOURCE"; exit 1; }
SLICEDIR=$GROUPDIR/size-$SIZE
mkdir -p "$SLICEDIR"
FILE=$(printf "%s/group-%02d.txt" "$SLICEDIR" "$INDEX")

# Non-comment AND non-blank, counted the same way the slice selects. Counting
# with `grep -vc '^#'` alone includes a trailing blank line: it reported 301
# tasks for a 300-task list, and at `--size 1` offered an empty group 301.
TOTAL=$(grep -v '^[[:space:]]*#' "$SOURCE" | grep -c '[^[:space:]]')
GROUPS_AVAILABLE=$(( (TOTAL + SIZE - 1) / SIZE ))
if [ "$INDEX" -lt 1 ] || [ "$INDEX" -gt "$GROUPS_AVAILABLE" ]; then
  echo "group $INDEX is out of range: $TOTAL task(s) at --size $SIZE gives $GROUPS_AVAILABLE group(s)"
  exit 1
fi

# Written to a temporary file and renamed into place.
#
# The slice path is derived from `--size` and `--index` alone, so several runs
# of the SAME slice — three models over the whole 300, say — all write
# `size-300/group-01.txt` at once. The content is identical, which makes the
# race invisible until a reader catches a half-written file and the run starts
# on a truncated task list. `mv` within one directory is atomic, so a reader
# sees either the old file or the whole new one.
grep -v '^[[:space:]]*#' "$SOURCE" | grep '[^[:space:]]' |
  sed -n "$(( (INDEX - 1) * SIZE + 1 )),$(( INDEX * SIZE ))p" > "$FILE.$$"
mv -f "$FILE.$$" "$FILE"
COUNT=$(grep -c . "$FILE")
[ "$COUNT" -gt 0 ] || { echo "group $INDEX is empty"; exit 1; }

echo "group   : $INDEX of $GROUPS_AVAILABLE  ($COUNT task(s) at --size $SIZE)"
echo "list    : $FILE"
echo "alloc   : ${ALLOC:-<none — containers run here>}"
# `${X:+a}${X:-b}` prints the value as well as the branch when X is set —
# `${X:-b}` falls back to X, not to b.
if [ -n "$CLUSTER" ]; then
  echo "model   : local cluster ($CLUSTER)"
elif [ -n "$SUBSCRIPTION" ]; then
  # Does not name a model: `--subscription` chooses the ACCOUNT, not the
  # model, and `--model` passes straight through to the harness. Naming Sonnet
  # here printed "hosted Claude Sonnet 5" for a run on Haiku.
  echo "model   : hosted Claude, on this account's subscription"
else
  echo "model   : hosted (Anthropic)"
fi
echo "shape   : $PARALLEL task(s) at once, every researched plan attempted"
if [ -n "$SUBSCRIPTION" ]; then
  echo "note    : subscription — the dollar figure is API-EQUIVALENT usage, not a bill"
elif [ -z "$CLUSTER" ]; then
  echo "note    : hosted — this spends real money; ceiling below"
fi
[ "${SPEND:-0}" != "0" ] && echo "budget  : \$$SPEND ceiling"
echo "store   : fresh, not carried — this group learns nothing from the others"
echo

# Which nodes run the benchmark's CONTAINERS: the allocation minus the fleet.
#
# With a local cluster the same allocation holds both, and they must not share a
# node — a node serving four llama-servers has no room for evaluation containers,
# and a container competing with a server slows the model for every task.
#
# The fleet's own membership comes from the per-GPU records each replica writes
# as it starts, which is the only place that reflects what actually came up:
# asked for 8 nodes this deploy landed 23 servers on 6, and anything reading the
# intended list would have put containers on two nodes that never served and
# skipped two that did.
#
# Unreachable hosts are dropped too. Two nodes in this allocation refuse ssh
# outright, and a container host that cannot be reached fails every task placed
# on it with "container host on X is not usable".
if [ -z "$NODES" ]; then
  RAW=""
  if [ -n "$ALLOC" ]; then
    RAW=$(flux proxy "$ALLOC" flux getattr hostlist 2>/dev/null | tail -1)
  else
    RAW=$(flux getattr hostlist 2>/dev/null | tail -1)
  fi
  NODES=$(CLUSTER="$CLUSTER" "$PBENCH/venv/bin/python" - "$RAW" <<'EOF' 2>/dev/null
import glob, json, os, re, subprocess, sys

text = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
match = re.match(r"^([A-Za-z][A-Za-z0-9-]*)\[(.*)\]$", text)
hosts = []
if match:
    stem, inner = match.group(1), match.group(2)
    for part in inner.split(","):
        if "-" in part:
            low, high = part.split("-", 1)
            hosts += [f"{stem}{n}" for n in range(int(low), int(high) + 1)]
        elif part:
            hosts.append(stem + part)
elif text:
    hosts = text.split()

serving = set()
config = os.environ.get("CLUSTER", "")
if config and os.path.exists(config):
    try:
        with open(config) as handle:
            run_dir = json.load(handle).get("run_dir", "")
        for record in glob.glob(os.path.join(run_dir, "nodes", "*.json")):
            with open(record) as handle:
                serving.add(json.load(handle).get("host", ""))
    except Exception:
        pass

free = [h for h in hosts if h not in serving]


def reachable(host):
    try:
        return subprocess.run(
            ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
             host, "true"], capture_output=True, timeout=12).returncode == 0
    except Exception:
        return False


# Probed CONCURRENTLY. Sequentially this is 16 hosts x up to 12s of connect
# timeout — over three minutes before the run can start, most of it spent
# waiting on the dead hosts it exists to find.
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=max(1, len(free))) as pool:
    alive = list(pool.map(reachable, free))
print(",".join(h for h, ok in zip(free, alive) if ok))
EOF
)
fi
[ -n "$NODES" ] && echo "hosts   : $NODES"

# `--reuse` has to bring a carry root with it, or it carries nothing.
#
# `--no-carry` gives each group its own store so a group that dies takes
# nothing with it, and that is right for a fresh run. But it also empties
# `--reuse` of meaning: the runner seeds earlier learning only when
# `carry_root` is set, so `--reuse` alone left the store as bare as `--fresh`
# and every reuse measurement came back zero. The two flags are one decision,
# so they are made in one place.
CARRY=(--no-carry)
for arg in "${EXTRA[@]}"; do
  if [ "$arg" = "--reuse" ]; then
    CARRY=(--carry-root "$PBENCH/carry/.phronix")
    echo "carry   : $PBENCH/carry/.phronix (what earlier runs learned)"
    break
  fi
done
CMD=("$PROJECT/scripts/run-benchmark.sh" --tasks "$FILE"
     --parallel-tasks "$PARALLEL" "${CARRY[@]}")
# A spend ceiling is for hosted models. On the local cluster the dollar figure
# is notional — the GPUs are yours and nothing is billed — so a cap there would
# stop a run over a number that means nothing.
[ -n "$CLUSTER" ] && CMD+=(--cluster "$CLUSTER")
[ "${SPEND:-0}" != "0" ] && CMD+=(--max-spend "$SPEND")
[ -n "$NODES" ] && CMD+=(--nodes "$NODES")
CMD+=("${EXTRA[@]}")

if [ -n "$ALLOC" ]; then
  flux proxy "$ALLOC" "${CMD[@]}"
else
  "${CMD[@]}"
fi

status=$?
[ $status -eq 0 ] && echo "group-$(printf '%02d' "$INDEX")" >> "$PBENCH/groups/done.txt"
exit $status
