#!/bin/bash
# Emit one line per matrix job that reaches a terminal state, then stop.
#
# Refreshes the model-matrix table in interesting.md whenever anything moves,
# so the notes track the sweep without anyone remembering to regenerate them.
#
# Every terminal state is reported, not just success: a sweep that dies is
# indistinguishable from a slow one if only completions are printed.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
PATTERN=${1:-livai-5\\.}

prev=""
while true; do
  # Matched against the NAME field, not the whole line. The line opens with
  # the job id, so an anchored name pattern (`^m2-`) matched nothing and the
  # watcher exited one second after it started, reporting "no matrix jobs
  # found" for a matrix that was running fine.
  all=$(flux jobs -a --no-header --format='{id.f58} {name} {status}' 2>/dev/null \
        | awk -v pat="$PATTERN" '$2 ~ pat' | sort)
  [ -z "$all" ] && { echo "no matrix jobs found"; exit 1; }

  cur=$(echo "$all" | awk '$3!="RUN" && $3!="SCHED" && $3!="DEPEND" && $3!="PENDING"' | sort)
  if [ "$cur" != "$prev" ]; then
    comm -13 <(echo "$prev") <(echo "$cur") | while read -r line; do
      [ -n "$line" ] && echo "$line"
    done
    python3 "$PROJECT/scripts/model-matrix.py" --write >/dev/null 2>&1
    prev=$cur
  fi

  done_n=$(echo "$cur" | grep -c . )
  total=$(echo "$all" | grep -c . )
  if [ "$done_n" -ge "$total" ]; then
    echo "matrix complete: $done_n/$total job(s) finished"
    python3 "$PROJECT/scripts/model-matrix.py" --write >/dev/null 2>&1
    exit 0
  fi
  sleep 300
done
