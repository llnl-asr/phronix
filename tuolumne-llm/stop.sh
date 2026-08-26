#!/bin/bash
# Tear down every fleet piece in the current allocation: the llama-server node jobs,
# the gateway job, and any servers those jobs orphaned (flux cancel does not
# reliably reap children).
#   flux proxy <alloc-jobid> tuolumne-llm/stop.sh
set -uo pipefail
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"

# 1. cancel our own jobs, matched by the names run-cluster.sh gives them
for name_prefix in llama- litellm-; do
    for j in $(flux jobs -f pending,running -no '{id} {name}' |
               awk -v p="$name_prefix" 'index($2,p)==1 {print $1}'); do
        flux cancel "$j" 2>/dev/null && echo "cancelled $j"
    done
done

# 2. reap orphaned servers: one reaper task on every node of the allocation
sleep 5
NALL=$(flux hostlist -e "$(flux getattr hostlist)" | wc -w)
flux run -N "$NALL" --tasks-per-node 1 -t 3m "$LLM_SCRIPTS/reap-node.sh" 2>&1 |
    grep -E 'reaped|killed'
echo STOPPED
