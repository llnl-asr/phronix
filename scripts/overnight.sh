#!/bin/bash
# Run groups back to back, one 60-minute pdebug allocation each.
#
# Written as a script rather than driven interactively because it outlives the
# session that starts it: each group needs its own allocation, and an
# allocation takes as long as it takes.
#
#   scripts/overnight.sh 2 10          # groups 2..10
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
source "$PROJECT/scripts/bench-root.sh"
PBENCH=$(bench_root)
INDEX=$PROJECT/interesting.md
LOG=$PBENCH/overnight.log
FIRST=${1:-2}
LAST=${2:-10}

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

note() {   # note <line> — appended to the index the user reads in the morning
    printf '%s\n' "$1" >> "$INDEX"
}

for g in $(seq "$FIRST" "$LAST"); do
    say "=== group $g: asking for an allocation"
    # --bg returns the id and detaches. `-t 60` is the wall limit the whole
    # cycle has to fit inside: ~5 minutes of fleet load, the rest is the run.
    alloc=$(flux alloc -N 8 -t 60 -q pdebug --bg 2>>"$LOG" | tr -d '[:space:]')
    if [ -z "$alloc" ]; then
        say "group $g: no allocation granted; stopping"
        note "- **group $g** — no allocation granted, not run"
        break
    fi
    say "group $g: allocation $alloc"

    # Wait for it to actually start. pdebug can queue.
    for _ in $(seq 1 120); do
        state=$(flux jobs -a --no-header 2>/dev/null | awk -v j="$alloc" '$1==j{print $5}')
        [ "$state" = "R" ] && break
        sleep 15
    done
    if [ "$(flux jobs -a --no-header 2>/dev/null | awk -v j="$alloc" '$1==j{print $5}')" != "R" ]; then
        say "group $g: allocation never started; skipping"
        note "- **group $g** — allocation $alloc never started"
        continue
    fi

    hosts=$(flux proxy "$alloc" flux getattr hostlist 2>/dev/null | tail -1)
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
    say "group $g: nodes $nodes"

    # --- fleet, on every node -------------------------------------------------
    dlog=/p/lustre5/haridev/llm-tuolumne/logs/deploy-g$g-$(date +%H%M%S).log
    flux proxy "$alloc" "$PROJECT/tuolumne-llm/deploy.sh" gptoss120 > "$dlog" 2>&1 &
    for _ in $(seq 1 40); do
        n=$(grep -oE "[0-9]+/32 ready" "$dlog" 2>/dev/null | tail -1 | cut -d/ -f1)
        [ "${n:-0}" -ge 28 ] 2>/dev/null && break
        sleep 20
    done
    ready=$(grep -oE "[0-9]+/32 ready" "$dlog" 2>/dev/null | tail -1)
    say "group $g: fleet ${ready:-unknown}"
    if [ -z "$ready" ] || [ "${ready%%/*}" -lt 8 ] 2>/dev/null; then
        say "group $g: fleet did not come up; skipping"
        note "- **group $g** — fleet failed (\`$dlog\`)"
        flux cancel "$alloc" 2>/dev/null
        continue
    fi

    # --- the run --------------------------------------------------------------
    rlog=$PBENCH/group$g-launch.log
    "$PROJECT/scripts/run-group.sh" "$g" "$alloc" --local --parallel 30 \
        --nodes "$nodes" > "$rlog" 2>&1 &
    runpid=$!
    sleep 45
    out=$(grep -E "^out " "$rlog" 2>/dev/null | awk '{print $3}')
    say "group $g: run ${out:-unknown}"

    # Wait for the run, or for the allocation to run out from under it.
    while kill -0 "$runpid" 2>/dev/null; do
        state=$(flux jobs -a --no-header 2>/dev/null | awk -v j="$alloc" '$1==j{print $5}')
        [ "$state" = "R" ] || { say "group $g: allocation ended; stopping the run"; break; }
        sleep 60
    done
    "$PROJECT/scripts/kill.sh" >/dev/null 2>&1
    flux cancel "$alloc" 2>/dev/null

    # --- what the morning needs ----------------------------------------------
    if [ -n "$out" ] && [ -d "$out" ]; then
        summary=$(cd "$PROJECT" && scripts/top.sh "$out" --once 2>/dev/null | sed -n 2p |
                  sed 's/^ *//' | cut -c1-150)
        skills=$(ls "$out"/claude-phronix/store/.phronix/capabilities/tasks/ 2>/dev/null | wc -l)
        used=$(grep -rh "skill-use" "$out"/*/tasks/*/trace.log 2>/dev/null | grep -c "loaded \`")
        note ""
        note "### group $g — \`$(basename "$out")\`"
        note ""
        note "\`\`\`"
        note "$summary"
        note "\`\`\`"
        note ""
        note "- run: \`$out\`"
        note "- fleet deploy: \`$dlog\` (${ready})"
        note "- skills written: **$skills**   attempts that loaded one: **$used**"
        note "- \`scripts/top.sh $out --once\`"
    else
        note "- **group $g** — run did not start (\`$rlog\`)"
    fi
    say "group $g: done"
done
say "all groups finished"
