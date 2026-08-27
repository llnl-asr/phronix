#!/bin/bash
# One batch job: bring up the fleet, run a slice of the task list, tidy up.
#
# Submitted, not run by hand:
#
#   scripts/bench-batch.sh --submit -N 32 -t 24h -q pbatch --size 300 --parallel 60
#   scripts/bench-batch.sh --submit -N 8  -t 60m -q pdebug --size 30 --index 4
#
# Without `--submit` it IS the payload, and expects to be inside the
# allocation — which is what `flux batch` gives it. Everything is co-located:
# the fleet takes every node, and the containers and agents run on those same
# nodes. On a 4-GPU node that is four llama-servers and a share of 96 cores,
# and the alternative is holding nodes back from the fleet to do work that is
# mostly waiting on the fleet.
#
# The whole cycle has to fit the wall limit: fleet load is ~5 minutes for
# gpt-oss-120b, and a task is ~20 minutes at three tries. `-t` is the ONE
# number that decides whether the tail completes or is cut off mid-attempt, so
# it is a required argument rather than a default that silently truncates.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
source "$PROJECT/scripts/bench-root.sh"
PBENCH=$(bench_root)

SUBMIT=""; NODES=8; WALL=""; QUEUE=pbatch
SIZE=30; INDEX=1; PARALLEL=30; MODEL=gptoss120; NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --submit)   SUBMIT=1; shift;;
    -N|--nodes) NODES="$2"; shift 2;;
    -t|--time)  WALL="$2"; shift 2;;
    -q|--queue) QUEUE="$2"; shift 2;;
    --size)     SIZE="$2"; shift 2;;
    --index)    INDEX="$2"; shift 2;;
    --parallel) PARALLEL="$2"; shift 2;;
    --model)    MODEL="$2"; shift 2;;
    --name)     NAME="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
NAME=${NAME:-bench-${SIZE}x${INDEX}}

if [ -n "$SUBMIT" ]; then
    [ -n "$WALL" ] || { echo "-t is required: it decides whether the tail finishes" >&2; exit 2; }
    out=$PBENCH/batch-$NAME-$(date +%m%d-%H%M%S).log
    # `flux batch` runs this same script INSIDE the allocation, with the same
    # arguments minus `--submit`. One file, so the thing submitted and the
    # thing that runs cannot drift apart.
    job=$(flux batch -N "$NODES" -t "$WALL" -q "$QUEUE" --job-name="$NAME" \
            --output="$out" \
            "$0" --size "$SIZE" --index "$INDEX" --parallel "$PARALLEL" \
                 --model "$MODEL" --name "$NAME" 2>&1 | tr -d '[:space:]')
    case "$job" in
      f*) echo "submitted $job   ($NODES nodes, $WALL, $QUEUE)"
          echo "  log      : $out"
          echo "  progress : scripts/top.sh --once"
          echo "  cancel   : flux cancel $job"
          printf '%s\n' "$job" > "$PBENCH/last-batch-job.txt";;
      *)  echo "submission failed: $job" >&2; exit 1;;
    esac
    exit 0
fi

# ---------------------------------------------------------------- the payload
say() { echo "[$(date +%H:%M:%S)] $*"; }
say "batch $NAME starting: size=$SIZE index=$INDEX parallel=$PARALLEL model=$MODEL"

# Inside the allocation, so no `flux proxy`: this process IS in it.
hosts=$(flux getattr hostlist 2>/dev/null | tail -1)
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
count=$(printf '%s' "$nodes" | tr ',' '\n' | grep -c .)
say "nodes ($count): $nodes"
[ "$count" -gt 0 ] || { echo "no nodes; not in an allocation?" >&2; exit 1; }

# ---- fleet, on every node ---------------------------------------------------
total=$((count * 4))
dlog=/p/lustre5/haridev/llm-tuolumne/logs/deploy-$NAME-$(date +%H%M%S).log
say "deploying $MODEL across $count node(s) -> $dlog"
"$PROJECT/tuolumne-llm/deploy.sh" "$MODEL" > "$dlog" 2>&1 &
deploy=$!
# Wait for MOST of it, not all: one replica that never loads must not hold a
# 24-hour job at the starting line.
want=$(( total * 85 / 100 ))
for _ in $(seq 1 90); do
    n=$(grep -oE "[0-9]+/$total ready" "$dlog" 2>/dev/null | tail -1 | cut -d/ -f1)
    [ "${n:-0}" -ge "$want" ] 2>/dev/null && break
    kill -0 "$deploy" 2>/dev/null || break
    sleep 20
done
ready=$(grep -oE "[0-9]+/$total ready" "$dlog" 2>/dev/null | tail -1)
say "fleet ${ready:-unknown}"
up=${ready%%/*}
case "$up" in
  ''|*[!0-9]*) say "fleet never reported readiness; stopping"; exit 1;;
esac
if [ "$up" -lt 4 ]; then
    say "fleet too small ($ready); stopping rather than measuring a starved run"
    exit 1
fi

# ---- the run ----------------------------------------------------------------
rlog=$PBENCH/$NAME-launch.log
say "running: size=$SIZE index=$INDEX parallel=$PARALLEL"
"$PROJECT/scripts/run-group.sh" "$INDEX" "" --local --parallel "$PARALLEL" \
    --size "$SIZE" --nodes "$nodes" > "$rlog" 2>&1
out=$(grep -E "^out " "$rlog" 2>/dev/null | awk '{print $3}')
say "run finished: ${out:-see $rlog}"

# ---- tidy up, and leave a note ---------------------------------------------
"$PROJECT/scripts/kill.sh" >/dev/null 2>&1
"$PROJECT/tuolumne-llm/stop.sh" >/dev/null 2>&1
if [ -n "$out" ] && [ -d "$out" ]; then
    {
      summary=$(cd "$PROJECT" && scripts/top.sh "$out" --once 2>/dev/null |
                sed -n 2p | sed 's/^ *//' | cut -c1-150)
      skills=$(ls "$out"/claude-phronix/store/.phronix/capabilities/tasks/ 2>/dev/null | wc -l)
      used=$(grep -rh "skill-use" "$out"/*/tasks/*/trace.log 2>/dev/null | grep -c "loaded \`")
      echo ""
      echo "### $NAME — \`$(basename "$out")\`  ($SIZE task(s), $count node(s))"
      echo ""
      echo '```'
      echo "$summary"
      echo '```'
      echo ""
      echo "- run: \`$out\`"
      echo "- fleet: \`$dlog\` (${ready})"
      echo "- skills written: **$skills**   attempts that loaded one: **$used**"
      echo "- \`scripts/top.sh $out --once\`"
    } >> "$PROJECT/interesting.md"
fi
say "batch $NAME done"
