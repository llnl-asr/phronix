#!/bin/bash
# Submit the whole 300-task list to pbatch as ten independent groups of thirty.
#
#   scripts/corona-300.sh              # submit all ten
#   scripts/corona-300.sh 3 7          # just groups 3..7
#   DRY=1 scripts/corona-300.sh        # print what would be submitted
#
# One `flux batch` job per group, each bringing up its own fleet and tearing it
# down after — so a group that dies takes nothing with it, and they run as the
# scheduler frees nodes rather than all at once.
#
# WALL is double what a group actually took, measured: 30 tasks at parallel 30
# on a 5-node fleet ran 3h30m wall. Doubling is the margin for a group whose
# tail is slower, and the job holds its allocation to the limit either way, so
# the cost of over-asking is queue position rather than wasted time.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
FIRST=${1:-1}
LAST=${2:-10}
NODES=${NODES:-8}
WALL=${WALL:-7h}
QUEUE=${QUEUE:-pbatch}
SIZE=${SIZE:-30}
PARALLEL=${PARALLEL:-30}

echo "submitting groups $FIRST..$LAST of $SIZE task(s)"
echo "  each: $NODES node(s), $WALL, $QUEUE, parallel $PARALLEL"
echo "  fleet takes 5 of 8 nodes (20 replicas); agents and containers take 3"
echo ""
for i in $(seq "$FIRST" "$LAST"); do
    if [ -n "${DRY:-}" ]; then
        echo "  would submit group $i"
        continue
    fi
    PHRONIX_FLEET=corona-llm "$PROJECT/scripts/bench-batch.sh" --submit \
        -N "$NODES" -t "$WALL" -q "$QUEUE" \
        --size "$SIZE" --index "$i" --parallel "$PARALLEL" \
        --fleet corona-llm --name "corona-g$i" 2>&1 | sed 's/^/  /'
    sleep 2
done
echo ""
echo "watch   : flux jobs -a | head -15"
echo "progress: scripts/top.sh --once"
echo "errors  : scripts/error-report.py <run-dir>"
