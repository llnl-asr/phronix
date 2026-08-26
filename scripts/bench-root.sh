#!/bin/bash
# Where the benchmark's workspace lives on THIS machine: venv, task lists, runs.
#
# Sourced by every script that needs it. Not a constant, because the workspace
# sits on a parallel filesystem and the clusters do not share one — /p/lustre5
# is Tuolumne's and is not mounted on corona, /p/lustre3 the other way about.
#
# The failure this exists to prevent is quiet and wastes a session: a hardcoded
# /p/lustre5 on corona does not error, it reports
#
#   no runs under /p/lustre5/haridev/phronix-bench/runs
#
# which reads as "your run is not there" rather than "I am looking on a
# filesystem this machine cannot see", while the run is going fine somewhere
# else. So: probe, and prefer the root that actually holds runs.
#
# PHRONIX_BENCH always wins, for a workspace somewhere neither candidate covers.
bench_root() {
    if [ -n "${PHRONIX_BENCH:-}" ]; then
        echo "$PHRONIX_BENCH"
        return
    fi
    local candidates=(/p/lustre5 /p/lustre4 /p/lustre3 /p/lustre2 /p/lustre1)
    local user first="" root
    user=$(id -un)
    # Two passes on purpose. A cluster can have several lustre mounts and a
    # phronix-bench directory on more than one of them (an old copy, or a root
    # created by a script that ran before any benchmark did), so "exists" is
    # not enough to identify the live one. A root holding runs is; a root that
    # merely exists is the fallback.
    for base in "${candidates[@]}"; do
        root=$base/$user/phronix-bench
        [ -d "$root" ] || continue
        [ -z "$first" ] && first=$root
        if [ -n "$(ls -A "$root/runs" 2>/dev/null)" ]; then
            echo "$root"
            return
        fi
    done
    echo "${first:-/p/lustre5/$user/phronix-bench}"
}
