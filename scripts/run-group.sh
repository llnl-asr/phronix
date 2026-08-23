#!/bin/bash
# Run one group of the SWE-bench lite list inside a named Flux allocation.
#
#   scripts/run-group.sh 1 f3TkgpQVfpEb              # group 1, that allocation
#   scripts/run-group.sh 2 f3TkgpQVfpEb --spend 100  # a different ceiling
#
# Sized so one group fits a short allocation: 34 tasks, ~$100, ~5 hours at 6
# tasks in parallel. Both numbers are enforced — the spend by the runner's own
# ceiling, the time only by how the group was sized, so watch the clock.
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
# `BENCH` collides with something in the login profile — it comes back
# as a session id, so paths built from it land in the wrong place.
PBENCH=/p/lustre5/haridev/phronix-bench
# NOT `GROUPS`: that is a bash builtin holding the user's group ids,
# and assigning to it is silently ignored — the path came out as the
# numeric gid, so every lookup missed.
GROUPDIR=$PBENCH/groups

INDEX=${1:-}
ALLOC=${2:-}
shift 2 2>/dev/null || true
[ -n "$INDEX" ] || { echo "usage: run-group.sh <index> <alloc-jobid> [options]"; exit 1; }

SPEND=0
PARALLEL=30
NODES=""
CLUSTER=$PROJECT/tuolumne-llm/cluster.json
EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --spend)    SPEND="$2"; shift 2;;
    --parallel) PARALLEL="$2"; shift 2;;
    --nodes)    NODES="$2"; shift 2;;
    --cluster)  CLUSTER="$2"; shift 2;;
    --hosted)   CLUSTER=""; shift;;
    *)          EXTRA+=("$1"); shift;;
  esac
done

FILE=$(printf "%s/group-%02d.txt" "$GROUPDIR" "$INDEX")
[ -f "$FILE" ] || { echo "no such group: $FILE"; echo "have:"; ls "$GROUPDIR" 2>/dev/null; exit 1; }
COUNT=$(grep -vc '^[[:space:]]*#' "$FILE" 2>/dev/null || grep -c . "$FILE")

echo "group   : $INDEX  ($COUNT task(s), $FILE)"
echo "alloc   : ${ALLOC:-<none — containers run here>}"
# `${X:+a}${X:-b}` prints the value as well as the branch when X is set —
# `${X:-b}` falls back to X, not to b.
if [ -n "$CLUSTER" ]; then
  echo "model   : local cluster ($CLUSTER)"
else
  echo "model   : hosted (Anthropic)"
fi
echo "shape   : $PARALLEL task(s) at once, every researched plan attempted"
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
             host, "true"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


print(",".join(h for h in free if reachable(h)))
EOF
)
fi
[ -n "$NODES" ] && echo "hosts   : $NODES"

CMD=("$PROJECT/scripts/run-benchmark.sh" --tasks "$FILE"
     --parallel-tasks "$PARALLEL" --no-carry)
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
