#!/bin/bash
# Resubmit any matrix job that hit its wall, once, with a longer one.
#
#   scripts/retry-timeouts.sh [name-pattern] [long-wall]
#
# The policy this implements: ask for 2.5h, because that is what a clean run
# needs and a short ask backfills far better on a contended queue; and when a
# run turns out to need more -- a couple of straggling task-arms drag it into
# a third and fourth pass -- give that ONE run 4h rather than paying the
# longer wall for all of them up front.
#
# Retried once and only once. The `-x4h` suffix is the record of that: a job
# already carrying it is never resubmitted again, so a run that cannot finish
# in four hours stops rather than looping.
set -uo pipefail
PROJECT=/usr/WS2/haridev/phronix
PBENCH=/p/lustre3/haridev/phronix-bench
PATTERN=${1:-^m2-}
LONG=${2:-4h}

declare -A SEEN=()

while true; do
  while read -r id name status; do
    case "$name" in *-x4h) continue;; esac          # already the long retry
    [ "$status" = TIMEOUT ] || continue
    [ -n "${SEEN[$name]:-}" ] && continue
    SEEN[$name]=1

    model=$(flux job info "$id" jobspec 2>/dev/null \
            | python3 -c 'import json,sys,re; print((re.search(r"--model (\S+)", " ".join(json.load(sys.stdin)["tasks"][0]["command"])) or [None,""])[1])')
    mode=fresh; case "$name" in *reuse*) mode=reuse;; esac
    [ -n "$model" ] || { echo "no model for $name; not retried"; continue; }

    new=$("$PROJECT/scripts/bench-batch.sh" --submit -N 8 -t "$LONG" -q pbatch \
            --size 30 --index 1 --parallel 30 --model "$model" \
            --name "$name-x4h" $([ "$mode" = reuse ] && echo --reuse) \
            --fleet tuolumne-llm --fleet-nodes 8 \
            --source "$PBENCH/lite-30-mixed.txt" --hosted \
            --harness claude --provider livai \
            --base-url https://livai-api.llnl.gov/v1 2>&1 \
          | grep -o 'f[A-Za-z0-9]\{11\}' | head -1)
    echo "retry $name at $LONG -> ${new:-SUBMIT FAILED}"
  done < <(flux jobs -a --no-header --format='{id.f58} {name} {status}' 2>/dev/null \
           | awk -v pat="$PATTERN" '$2 ~ pat')
  sleep 180
done
