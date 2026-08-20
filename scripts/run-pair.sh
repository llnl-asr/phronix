#!/bin/bash
# The reuse experiment: the same tasks twice, fresh then reusing.
#
#   run-pair.sh --node tuolumne1075
#   run-pair.sh --node tuolumne1075 --tasks fast-6.txt
#
# Run one asks the question the benchmark exists for: does phronix help an agent
# starting from nothing. Run two asks the question the system is FOR: having
# researched these subjects once, is the second encounter cheaper.
#
# They must be sequential, not concurrent. The reuse run inherits what the fresh
# run synced into the project layer when it ended, so starting them together
# would give run two an empty store and measure nothing.
set -uo pipefail

SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BENCH=/p/lustre5/haridev/phronix-bench
ARGS=("$@")

# A store of the pair's own, empty at the start.
#
# The project layer already holds what earlier runs accumulated, and run two
# reading THAT would measure reuse of everything ever learned rather than reuse
# of what run one just found. Which is a fair question, but not this one — and
# it would silently include research produced while the pipeline was broken.
CARRY=${PHRONIX_PAIR_CARRY:-$BENCH/pair-carry-$(date +%m%d-%H%M%S)}
mkdir -p "$CARRY"
ARGS+=(--carry-root "$CARRY")
echo "carry root for this pair: $CARRY"
echo

echo "=== run 1 of 2: FRESH ==="
"$SCRIPTS/run-benchmark.sh" "${ARGS[@]}" --fresh --tag pair-fresh || exit 1
FRESH=$(cat "$BENCH/CURRENT")

# Wait for it to finish. The runner writes results as it goes, so "finished" is
# the process exiting, not the file being complete.
while pgrep -f -- "$BENCH/venv/bin/python -u -m tests.benchmark.cli run" >/dev/null; do
  sleep 60
done
echo "run 1 finished: $FRESH"

# What it learned is now in the project layer. Show it, because an empty carry
# root would make run two a second fresh run wearing a different label — and
# nothing in the results themselves would reveal that.
echo "carried into $CARRY:"
for kind in skills research capabilities; do
  n=$(find "$CARRY/$kind" -type f 2>/dev/null | wc -l)
  echo "  $kind: $n file(s)"
done

sleep 30
echo
echo "=== run 2 of 2: REUSE ==="
"$SCRIPTS/run-benchmark.sh" "${ARGS[@]}" --reuse --tag pair-reuse || exit 1
REUSE=$(cat "$BENCH/CURRENT")

while pgrep -f -- "$BENCH/venv/bin/python -u -m tests.benchmark.cli run" >/dev/null; do
  sleep 60
done
echo "run 2 finished: $REUSE"

echo
echo "=== compare ==="
"$SCRIPTS/status.sh" "$(basename "$FRESH")"
"$SCRIPTS/status.sh" "$(basename "$REUSE")"
