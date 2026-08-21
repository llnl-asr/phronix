#!/bin/bash
# Is the research pipeline actually producing anything?
#
#   research-progress.sh            # the most recent run
#   research-progress.sh <run-dir>
#
# `status.sh` shows which stage a task is in. That is not the same question. A
# run can advance through every stage and record nothing: measured on one fleet,
# all six tasks walked survey -> plan -> collect -> propose while the research
# records held aspects=0 and approaches=0, because the planner narrated its plan
# instead of calling `research_set_aspects`. The trace looked healthy and the
# investigation phase had been skipped in silence.
#
# So this asks the pipeline for its OUTPUT rather than its position:
#
#   stages     which of the eleven stages each task has reached
#   candidates aspects and approaches actually on record
#   tools      whether the agent is driving the protocol or just exploring
#
# A task with stages but no candidates is the failure this exists to surface.
set -uo pipefail

BENCH=/p/lustre5/haridev/phronix-bench
RUN="${1:-$(ls -dt "$BENCH"/runs/*/ 2>/dev/null | head -1)}"
RUN="${RUN%/}"
[ -d "$RUN" ] || { echo "no run at $RUN" >&2; exit 2; }
echo "run: $RUN"

for arm in "$RUN"/*phronix*/; do
  [ -d "$arm/tasks" ] || continue
  echo
  echo "=== $(basename "$arm")"

  # -- 1. how far each task got, and what it has to show for it ---------------
  printf "  %-26s %-46s %s\n" task "stages reached" "candidates"
  for t in "$arm"/tasks/*/; do
    name=$(basename "$t" | cut -c5-)
    stages=$(grep -ohE "research>[a-z:-]+>|attempt>|evaluate>" "$t/trace.log" 2>/dev/null \
             | sed 's/research>//; s/>//' | awk '!seen[$0]++' | tr '\n' ' ')
    # The record is the truth; the trace only says where the agent was.
    counts=$(python3 - "$name" "$RUN" <<'PY' 2>/dev/null
import glob, json, os, sys
task = sys.argv[1]
# Records are named for the topic, which is derived from the instance id.
# A --fresh run writes into its OWN session store, not the project layer:
# <run>/<arm>/store/.phronix/research/sessions/<run>/<topic>.json. Reading the
# project layer showed stale records from earlier runs, or none at all.
run = sys.argv[2]
hits = [f for f in glob.glob(f"{run}/*/store/.phronix/research/**/*.json",
                             recursive=True)
        if task.replace("__", "-") in os.path.basename(f)]
if not hits:
    hits = [f for f in glob.glob("/usr/WS2/haridev/phronix/.phronix/research/*.json")
            if task.replace("__", "-") in os.path.basename(f)]
if not hits:
    print("- ")
    raise SystemExit
d = json.load(open(max(hits, key=os.path.getmtime)))
fom = (d.get("fom") or {}).get("name") or "-"
print(f"{len(d.get('aspects') or []):>2} asp {len(d.get('approaches') or []):>2} appr "
      f"{len(d.get('instances') or []):>2} inst  fom={fom}")
PY
)
    printf "  %-26s %-46s %s\n" "$name" "${stages:-(starting)}" "${counts:-?}"
  done

  # -- 2. is the agent driving the protocol at all? ---------------------------
  #
  # The pipeline depends on ~10 recording tools being called in sequence. A
  # model that calls the first one and then explores the repository leaves the
  # record empty however busy the trace looks. Five calls across a whole
  # six-task run is what that failure measured.
  echo
  echo "  phronix tools called:"
  grep -ohE "phronix: [a-z ]+|research [a-z_ ]+" "$arm/trace.log" 2>/dev/null \
    | sed 's/phronix: //' | sort | uniq -c | sort -rn | head -10 | sed 's/^/    /'
  total=$(grep -ohE "phronix: |research [a-z_]+" "$arm/trace.log" 2>/dev/null | wc -l | tr -d ' ')
  echo "    ---- ${total:-0} call(s) total"

  # -- 3. the correctors, which only fire when the model fails -----------------
  for pattern in "recorded NO aspects" "asking again" "salvaged" \
                 "still running past its" "KILLED at the"; do
    # -h so a multi-file match cannot return one count per file, which turns
    # the comparison below into `[: 0\n0: integer expression expected`.
    n=$(grep -ho "$pattern" "$arm/trace.log" 2>/dev/null | wc -l | tr -d ' ')
    [ "${n:-0}" -gt 0 ] && echo "  ** $n x \"$pattern\""
  done
done
echo
echo "(a task with stages but 0 aspects means the planner narrated instead of recording)"
