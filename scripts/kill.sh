#!/bin/bash
# Stop every benchmark process. Usage: kill.sh [--dry-run]
#
# Safety note, and the reason this is not `pkill -f claude`: the user runs an
# interactive Claude Code session in VS Code, and the benchmark spawns agents
# with the same binary name. Killing by binary would kill the session issuing
# the kill. So agents are matched on the BENCHMARK RUN PATH, which appears in
# every spawned agent's argv (--add-dir / --dir) and in nothing else.
set -uo pipefail

BENCH=/p/lustre5/haridev/phronix-bench
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
