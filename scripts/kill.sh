#!/bin/bash
# Stop every benchmark process. Usage: kill.sh [--dry-run]
#
# Safety note, and the reason this is not `pkill -f claude`: the user runs an
# interactive Claude Code session in VS Code, and the benchmark spawns agents
# with the same binary name. Killing by binary would kill the session issuing
# the kill. So agents are matched on the BENCHMARK RUN PATH, which appears in
# every spawned agent's argv (--add-dir / --dir) and in nothing else.
set -uo pipefail

# Per-CLUSTER, like run-group.sh: /p/lustre5 is Tuolumne's and is not mounted
# on corona, so a corona run's processes are matched against a corona path.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bench-root.sh"
BENCH=$(bench_root)
RUNS="$BENCH/runs"
VENV=$BENCH/venv
DRY=""
[ "${1:-}" = "--dry-run" ] && DRY=1

# Patterns, most specific first. Each must be unable to match this script or an
# interactive session.
RUNNER="$VENV/bin/python -u -m tests.benchmark.cli run"
WATCHER="launch-when-ready.sh"

# Never kill this process, its parent, or anything mentioning kill.sh.
#
# `pkill -f` matches the whole command line, and the shell that INVOKES this
# script has the script's name in its own argv — so a naive pkill killed the
# caller mid-run and the watcher survived, twice. Ancestors are excluded
# explicitly rather than hoped about.
mine="$$ $PPID"
matching() {   # matching <pattern> -> pids, excluding self and ancestors
  local pattern="$1" pid out=""
  for pid in $(pgrep -f -- "$pattern" 2>/dev/null); do
    case " $mine " in *" $pid "*) continue;; esac
    ps -o args= -p "$pid" 2>/dev/null | grep -q "kill\.sh" && continue
    out="$out $pid"
  done
  echo "${out# }"
}

show() {   # show <label> <pattern>
  local pids
  pids=$(matching "$2")
  [ -n "$pids" ] && echo "  $1: $pids"
}

echo "processes matched:"
show "runner " "$RUNNER"
show "watcher" "$WATCHER"

# Agents: any claude/opencode process whose argv mentions the runs directory.
agents=$(ps -eo pid,args --no-headers 2>/dev/null \
  | grep -E "(claude|opencode)" \
  | grep -F "$RUNS" \
  | grep -v "kill.sh" \
  | awk '{print $1}' | tr '\n' ' ')
[ -n "${agents// /}" ] && echo "  agents : $agents"

if [ -n "$DRY" ]; then
  echo "(dry run — nothing killed)"
  exit 0
fi

# Runner first: it is what spawns replacements. Then the agents it left behind.
# By pid, never by pkill, so the caller cannot be caught in the pattern.
for pid in $(matching "$RUNNER") $(matching "$WATCHER"); do
  kill "$pid" 2>/dev/null
done
sleep 2
for pid in $(matching "$RUNNER") $(matching "$WATCHER"); do
  kill -9 "$pid" 2>/dev/null
done
sleep 1
for pid in $agents; do kill "$pid" 2>/dev/null; done
sleep 2
for pid in $agents; do kill -9 "$pid" 2>/dev/null; done

# Runs recorded on OTHER hosts.
#
# The process table is node-local, so a run launched from a different node is
# invisible here — `pgrep` says "not running" while the account is still being
# charged. scripts/go.sh writes the pid and host of every run it starts; this
# walks those and reaches across.
LOGS=/usr/WS2/haridev/phronix/logs
if [ -d "$LOGS" ]; then
  for entry in "$LOGS"/*.json; do
    [ -f "$entry" ] || continue
    host=$(python3 -c "import json;print(json.load(open('$entry')).get('host',''))" 2>/dev/null)
    pid=$(python3 -c "import json;print(json.load(open('$entry')).get('pid',''))" 2>/dev/null)
    [ -n "$host" ] && [ -n "$pid" ] || continue
    if [ "$host" = "$(hostname)" ]; then
      kill -9 "$pid" 2>/dev/null && echo "  killed local pid $pid ($(basename "$entry" .json))"
    else
      if timeout 20 ssh -o BatchMode=yes "$host" "kill -9 $pid" 2>/dev/null; then
        echo "  killed pid $pid on $host ($(basename "$entry" .json))"
      fi
    fi
    # The record has served its purpose; leaving it makes every later kill
    # re-attempt processes that are long gone.
    rm -f "$entry"
  done
fi

rm -f "$RUNS/.runner.lock"

# Remove the containers the stopped run left behind.
#
# Not tidiness — correctness. Every container holds kernel session keys, and the
# per-user quota is 200. A run killed mid-flight leaves its containers running:
# 91 of them had accumulated here, holding 179 of the 200 keys, and the next run
# died on every task with
#
#   runc create failed: unable to join session keyring: disk quota exceeded
#
# which names neither containers nor keys and reads like a full disk. Pruning
# here, where a run is already being torn down, is what keeps the next one from
# inheriting the problem.
#
# Only the benchmark's own store is touched, so a container belonging to
# anything else on this machine is left alone.
if [ -z "$DRY" ]; then
  # The store is resolved ON EACH HOST, because it is node-dependent.
  #
  # This was hardcoded to /tmp/$USER/phronix-images. The runner picks the first
  # writable node-local scratch, which is /l/ssd on a compute node and /tmp on
  # a login node — so the prune ran against an empty store, reported success,
  # and left every container of every killed run alive: 55 across two nodes,
  # holding keyring keys against a quota of 200, which is the exact failure
  # this prune exists to prevent.
  #
  # Resolving it locally would have reproduced the bug with a different path,
  # so the resolution is part of what runs remotely.
  reaper='
    S=$(PY -c "
import sys; sys.path.insert(0, \"/usr/WS2/haridev/phronix/tests\")
from benchmark.paths import image_store
print(image_store()[\"root\"].rsplit(\"/\", 1)[0])" 2>/dev/null)
    [ -n "$S" ] && [ -d "$S" ] || { echo "  ** no image store resolved"; exit 0; }
    n=$(podman --root "$S/storage" --runroot "$S/run" ps -aq 2>/dev/null | wc -l)
    [ "$n" -gt 0 ] && podman --root "$S/storage" --runroot "$S/run" rm -f -a >/dev/null 2>&1
    [ "$n" -gt 0 ] && echo "  containers removed: $n"
    # Reaping a container is not the same as reaping its monitor. A container
    # removed while conmon is mid-flight leaves the monitor behind: 30 here,
    # the oldest four and a half hours old, surviving every kill of every run.
    # Small (~3 MB each) but they accumulate for as long as the node is up.
    m=0
    for c in /proc/[0-9]*/cmdline; do
      grep -qa "$S" "$c" 2>/dev/null || continue
      grep -qa conmon "$c" 2>/dev/null || continue
      pid=${c#/proc/}; pid=${pid%/cmdline}
      kill -9 "$pid" 2>/dev/null && m=$((m+1))
    done
    [ "$m" -gt 0 ] && echo "  monitors reaped: $m"
    exit 0'
  reaper=${reaper//PY/$VENV/bin/python}

  for host in ${BENCH_NODES:-$(hostname)}; do
    if [ "$host" = "$(hostname)" ]; then
      bash -c "$reaper" | sed "s/^/  [$host]/"
    else
      ssh -n -o BatchMode=yes "$host" "bash -c '$reaper'" 2>/dev/null \
        | sed "s/^/  [$host]/"
    fi
  done
fi

# Confirm, rather than assume. A kill that silently failed is worse than none:
# it reads as "stopped" while the account keeps being charged.
left=$(matching "$RUNNER")$(matching "$WATCHER")
still=$(ps -eo pid,args --no-headers 2>/dev/null \
  | grep -E "(claude|opencode)" | grep -F "$RUNS" | grep -v kill.sh \
  | awk '{print $1}' | tr '\n' ' ')

if [ -z "${left// /}" ] && [ -z "${still// /}" ]; then
  echo "all stopped; lock cleared"
else
  echo "STILL RUNNING — runner: ${left:-none}  agents: ${still:-none}" >&2
  exit 1
fi
