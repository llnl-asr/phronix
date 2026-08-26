#!/bin/bash
# Kill every llama-server this deployment recorded for THIS node.
# Only kills pids that are still ours and still the llama-server binary.
set -uo pipefail
# Resolve env.sh NEXT TO THIS SCRIPT, not from a hardcoded path: corona-llm/
# symlinks these scripts and carries its own env.sh, and a hardcoded default
# would have every corona invocation silently load Tuolumne's paths and arch.
source "${LLM_SCRIPTS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}/env.sh"
HOSTN=$(hostname)
PIDDIR=$LLM_ROOT/logs/pids
shopt -s nullglob

killed=0
for pf in "$PIDDIR/$HOSTN-"*.pid; do
    pid=$(cat "$pf" 2>/dev/null)
    if [[ $pid =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null &&
       [[ -O /proc/$pid && $(readlink -f "/proc/$pid/exe" 2>/dev/null) == "$LLAMA_SERVER" ]]; then
        kill -TERM "$pid" 2>/dev/null
        for _ in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
        kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null
        echo "[$HOSTN] killed $pid ($(basename "$pf"))"
        killed=$((killed + 1))
    fi
    rm -f "$pf"
done
# Second pass for servers started before pidfiles existed: match on our own uid
# AND the exact build-mi300a/bin/llama-server executable, nothing else.
for pid in $(pgrep -u "$(id -u)" -x llama-server 2>/dev/null); do
    [[ $(readlink -f "/proc/$pid/exe" 2>/dev/null) == "$LLAMA_SERVER" ]] || continue
    kill -TERM "$pid" 2>/dev/null
    for _ in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null
    echo "[$HOSTN] killed untracked $pid"
    killed=$((killed + 1))
done

echo "[$HOSTN] reaped $killed llama-server process(es)"
