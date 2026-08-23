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

SPEND=100
PARALLEL=6
NODES=2
EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --spend)    SPEND="$2"; shift 2;;
    --parallel) PARALLEL="$2"; shift 2;;
    --nodes)    NODES="$2"; shift 2;;
    *)          EXTRA+=("$1"); shift;;
  esac
done

FILE=$(printf "%s/group-%02d.txt" "$GROUPDIR" "$INDEX")
[ -f "$FILE" ] || { echo "no such group: $FILE"; echo "have:"; ls "$GROUPDIR" 2>/dev/null; exit 1; }
COUNT=$(grep -vc '^[[:space:]]*#' "$FILE" 2>/dev/null || grep -c . "$FILE")

echo "group   : $INDEX  ($COUNT task(s), $FILE)"
echo "alloc   : ${ALLOC:-<none — containers run here>}"
echo "budget  : \$$SPEND ceiling, $PARALLEL task(s) in parallel, $NODES node(s)"
echo "store   : fresh, not carried — this group learns nothing from the others"
echo

run() {
  "$PROJECT/scripts/run-benchmark.sh" \
      --tasks "$FILE" --max-spend "$SPEND" \
      --parallel-tasks "$PARALLEL" --nodes "$NODES" \
      --no-carry "${EXTRA[@]}"
}

if [ -n "$ALLOC" ]; then
  flux proxy "$ALLOC" bash -c "$(declare -f run); run"
else
  run
fi

status=$?
[ $status -eq 0 ] && echo "group-$(printf '%02d' "$INDEX")" >> "$PBENCH/groups/done.txt"
exit $status
