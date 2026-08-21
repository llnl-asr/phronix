#!/bin/bash
# Copy a model onto every node's local SSD with dcp, so servers load locally.
#
#   flux proxy <alloc-jobid> tuolumne-llm/stage-models.sh gptoss120
#   flux proxy <alloc-jobid> tuolumne-llm/stage-models.sh gptoss120 nemosuper
#   MODEL_CACHE=/l/ssd/$USER/models ... stage-models.sh gptoss120
#
# Why this exists:
#
# Every llama-server reads its weights off lustre at startup, and gpt-oss-120b
# is 63 GB. Eight nodes starting together ask the PFS for half a terabyte at
# once, and it does not deliver it evenly — measured on an unstaggered launch,
# 20 of 32 servers were healthy at five minutes while three whole nodes were
# still short of ready at fourteen, weights resident but KV not yet allocated.
# Nothing was broken; they were starved of read bandwidth.
#
# Staggering hides that; staging removes it. One parallel copy per node up
# front, and every server after that loads from local xfs. It also makes restart
# cheap, which matters when a profile change means bringing the fleet back up.
#
# The four servers on a node share one file, so the page cache serves the second
# through fourth from memory either way — the win is lustre being read once per
# node instead of concurrently by everyone.
set -uo pipefail
source "${LLM_SCRIPTS:-/usr/WS2/haridev/phronix/tuolumne-llm}/env.sh"

#: Node-local, on real disk. NOT /tmp — that is tmpfs on these nodes, so a
#: staged model would be held in RAM and taken straight back out of the memory
#: the weights and KV need.
MODEL_CACHE=${MODEL_CACHE:-/l/ssd/$(id -un)/models}

#: dcp ranks per node.
#:
#: High on purpose: a 63 GB file across many ranks keeps both lustre's stripes
#: and the local SSD's queues busy, and these nodes have 96 cores doing nothing
#: while the fleet is down.
PPN=${PPN:-64}

MPIFILEUTILS_MODULE=${MPIFILEUTILS_MODULE:-mpifileutils/0.12}

[ $# -gt 0 ] || { echo "usage: stage-models.sh <model-key> [model-key...]" >&2; exit 2; }

# Resolve each key to the file env.sh declares for it.
declare -A SOURCE=(
    [nemotron]="$MODEL_NEMOTRON"
    [muse]="$MODEL_MUSE"
    [ornith]="$MODEL_ORNITH"
    [gptoss120]="${MODEL_GPTOSS120:-}"
    [gptoss20]="${MODEL_GPTOSS20:-}"
    [nemosuper]="${MODEL_NEMOSUPER:-}"
)

read -r -a HOSTS <<< "$(flux hostlist -e "$(flux getattr hostlist)")"
NNODES=${#HOSTS[@]}
echo "staging onto $NNODES node(s): ${HOSTS[*]}"
echo "destination: $MODEL_CACHE  ($PPN dcp process(es) per node)"

for key in "$@"; do
    src=${SOURCE[$key]:-}
    if [ -z "$src" ]; then
        echo "unknown model key '$key' (have: ${!SOURCE[*]})" >&2
        exit 2
    fi
    if [ ! -f "$src" ]; then
        echo "no such model file for '$key': $src" >&2
        exit 2
    fi

    # Sharded models: copy the whole directory, since llama.cpp opens the first
    # shard and finds its siblings beside it.
    if [[ $(basename "$src") == *-00001-of-* ]]; then
        from=$(dirname "$src")
        leaf=$(basename "$from")
    else
        from=$src
        leaf=$(basename "$src")
    fi
    size=$(du -sb "$from" 2>/dev/null | cut -f1)
    echo
    echo "=== $key: $from  ($(numfmt --to=iec "${size:-0}" 2>/dev/null || echo "$size B"))"

    # ONE dcp per node, not one across the allocation.
    #
    # dcp assumes a shared destination and splits the work by rank. Pointed at a
    # node-local path it does exactly that — measured, a single collective copy
    # left each node holding a different fraction of the file (7.9 GB, 15.9 GB,
    # 23.8 GB ...), because each rank wrote only its own chunk to whichever host
    # it landed on. The result looks like a copy and loads like a corrupt file.
    #
    # So the parallelism goes INSIDE a node: PPN ranks all on one host, copying
    # the whole file to that host's disk. The nodes then run concurrently
    # because the launches are backgrounded.
    pids=()
    for h in "${HOSTS[@]}"; do
        (
            flux run -N1 -n "$PPN" --requires="host:$h" -t 60m \
                bash -c "
                    module load $MPIFILEUTILS_MODULE >/dev/null 2>&1
                    mkdir -p '$MODEL_CACHE'
                    exec dcp '$from' '$MODEL_CACHE/$leaf'
                " > "/tmp/dcp-$h.log" 2>&1
            rc=$?
            echo "    $h: copy finished (rc=$rc)"
        ) &
        pids+=($!)
    done
    for pid in "${pids[@]}"; do wait "$pid"; done

    echo "  verifying on each node:"
    flux run -N "$NNODES" --tasks-per-node 1 -t 10m \
        bash -c "
            # Allocated bytes, not apparent: a sparse or partial copy has the
            # right length and the wrong contents, which is the failure mode a
            # shared-destination dcp produces.
            got=\$(du -s --block-size=1 '$MODEL_CACHE/$leaf' 2>/dev/null | cut -f1)
            if [ \"\${got:-0}\" -ge '$size' ]; then
                echo \"    \$(hostname): ok\"
            else
                echo \"    \$(hostname): MISMATCH \${got:-missing} vs $size\" >&2
            fi
        " 2>&1 | sort | head -"$NNODES"
done

echo
echo "staged. Point the servers at the local copies with:"
echo "  MODEL_CACHE=$MODEL_CACHE  (gpu-server.sh prefers it automatically)"
