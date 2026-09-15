#!/bin/bash
# Archive finished run directories into one tar each, in parallel.
#
#   scripts/archive-runs.sh <candidates-file> [jobs]
#
# A run directory holds 300-500k files and the benchmark's filesystem is
# limited by INODES, not bytes: 29M files against a 29.15M hard limit, with
# 39T of 75T used. One tar per run turns ~400k inodes into 1 and keeps every
# byte, recoverable with `tar -xf`. Serially it is hours of walking small
# files on a parallel filesystem; the work is per-directory and independent,
# so it parallelises exactly.
#
# Verify before delete, always. A tar that truncated -- which is precisely
# what a full filesystem causes -- would otherwise take the original with it.
set -uo pipefail
RUNS=/p/lustre3/haridev/phronix-bench/runs
ARCHIVE=/p/lustre3/haridev/phronix-bench/runs-archive
LIST=${1:?usage: archive-runs.sh <candidates-file> [jobs]}
JOBS=${2:-24}

mkdir -p "$ARCHIVE"

one() {
    d=$1
    [ -d "$RUNS/$d" ] || { echo "skip $d (gone)"; return 0; }
    if tar -cf "$ARCHIVE/$d.tar" -C "$RUNS" "$d" 2>/dev/null \
       && tar -tf "$ARCHIVE/$d.tar" >/dev/null 2>&1; then
        rm -rf "${RUNS:?}/$d" && echo "ok $d"
    else
        rm -f "$ARCHIVE/$d.tar"
        echo "FAIL $d (left in place)"
    fi
}
export -f one
export RUNS ARCHIVE

grep -v '^[[:space:]]*$' "$LIST" | xargs -P "$JOBS" -I{} bash -c 'one "$@"' _ {}
