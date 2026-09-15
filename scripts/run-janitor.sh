#!/bin/bash
# Drop the per-task scratch of FINISHED runs, on a loop, while a sweep runs.
#
#   scripts/run-janitor.sh [interval-seconds] [quiet-seconds]
#
# A complete 30-task run costs ~726k inodes, and a 5x2x3 matrix is therefore
# ~15M against ~16M of headroom -- it fits once and then wedges the
# filesystem, which is exactly how last night went. Two subdirectories per
# task account for 40% of that and nothing reads either:
#
#   cache/        per-task container and graph scratch
#   store-after/  a snapshot the runner WRITES (runner.py:3110) and never
#                 reads back
#
# What every figure and the tracking table read is left alone: results.jsonl,
# report.json, trace.jsonl, retrievals.jsonl, manifest.json, the run-level
# store/, and attempt-*/ (which `reuse.sh` reads to find learned-tool calls).
#
# Only touches runs that have gone QUIET, so a live task is never robbed of
# its own scratch mid-attempt.
set -uo pipefail
RUNS=/p/lustre3/haridev/phronix-bench/runs
EVERY=${1:-900}
QUIET=${2:-1800}

while true; do
  now=$(date +%s)
  freed=0
  for d in "$RUNS"/*/; do
    [ -d "$d" ] || continue
    newest=$(find "$d" -maxdepth 4 -name "*.jsonl" -o -maxdepth 4 -name "*.log" 2>/dev/null \
             | head -40 | xargs -r stat -c %Y 2>/dev/null | sort -rn | head -1)
    [ -n "$newest" ] || continue
    [ $(( now - newest )) -lt "$QUIET" ] && continue      # still working
    for sub in cache store-after; do
      while IFS= read -r victim; do
        rm -rf "$victim" && freed=$((freed + 1))
      done < <(find "$d" -mindepth 4 -maxdepth 4 -type d -name "$sub" 2>/dev/null)
    done
  done
  [ "$freed" -gt 0 ] && echo "$(date +%H:%M) janitor: cleared $freed scratch dir(s)"
  sleep "$EVERY"
done
