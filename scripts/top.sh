#!/bin/bash
# `top` for a benchmark run.  Usage:
#
#   top.sh                    the newest run, interactively
#   top.sh <run>              that run (name or path)
#   top.sh --once             one frame to stdout, for a pipe or `watch`
#   top.sh --list [N]         the last N runs, newest first
#
# The screen is a hierarchy and opens the way `top` does:
#
#   run header    what this run is, how far it has got, how fast
#   arm           one row per arm — pass / fail / running, tokens, cost
#     task        one row per task, like a process row
#       detail    opened on demand — tries, research, trials, live trace
#
# keys:  up/down move   enter open/close   right/left open/close
#        s sort (state, time, name, cost)  f filter (all/running/failed/passed)
#        a open everything   c collapse tasks   l page the task's trace   q quit
#
# This is the watching tool; `status.sh` is the reporting one. status.sh prints
# everything it knows, which is right for a file and wrong for a screen: a
# 30-task run scrolls several times over, so the totals and the one stuck task
# are never visible together.
set -uo pipefail

SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPTS/bench-root.sh"
BENCH=$(bench_root)
RUNS="$BENCH/runs"

# The benchmark's own venv when there is one: this reads only the standard
# library, but the system python3 on a login node is not guaranteed to be one
# that runs at all.
PY=$BENCH/venv/bin/python
[ -x "$PY" ] || PY=$(command -v python3)

case "${1:-}" in
  -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  --list)
    ls -dt "$RUNS"/*/ 2>/dev/null | head -"${2:-5}" |
      while read -r run; do basename "${run%/}"; done
    exit 0;;
esac

export PHRONIX_BENCH="$BENCH"
export COLUMNS=${COLUMNS:-$(tput cols 2>/dev/null || echo 160)}
exec "$PY" "$SCRIPTS/bench_top.py" "$@"
