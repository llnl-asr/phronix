#!/bin/bash
# Is anything running, and what is it costing? Usage: running.sh
#
# `status.sh` answers "how is the run going". This answers the more urgent
# question: is anything spending money right now, and what would I kill.
set -uo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bench-root.sh"
BENCH=$(bench_root)
# Scripts live in the project; only DATA lives on the PFS.
SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RUNS="$BENCH/runs"
VENV=$BENCH/venv
RUNNER="$VENV/bin/python -u -m tests.benchmark.cli run"

echo "host: $(hostname)   $(date '+%F %T')"
echo

runner=$(pgrep -f -- "$RUNNER" 2>/dev/null | tr '\n' ' ')
if [ -n "${runner// /}" ]; then
  echo "RUNNER RUNNING: pid $runner"
  ps -o pid,etime,args --no-headers -p ${runner% } 2>/dev/null \
    | sed 's/  */ /g' | cut -c1-150 | sed 's/^/  /'
else
  echo "runner: not running on this node"
fi

watcher=$(pgrep -f "launch-when-ready.sh" 2>/dev/null | tr '\n' ' ')
[ -n "${watcher// /}" ] && echo "WATCHER RUNNING: pid $watcher (will launch a run when the API clears)"

# Agents matched by the run path, never by binary name — an interactive Claude
# Code session shares the binary and must not be reported as benchmark spend.
echo
agents=$(ps -eo pid,etime,args --no-headers 2>/dev/null \
  | grep -E "(claude|opencode)" | grep -F "$RUNS" | grep -v running.sh)
if [ -n "$agents" ]; then
  echo "AGENTS SPENDING NOW:"
  echo "$agents" | sed 's/  */ /g' | cut -c1-140 | sed 's/^/  /'
else
  echo "agents: none spending"
fi

# Runs recorded on other hosts, which this node cannot see in ps.
LOGS=/usr/WS2/haridev/phronix/logs
if [ -d "$LOGS" ] && ls "$LOGS"/*.json >/dev/null 2>&1; then
  echo
  echo "RUNS RECORDED (may be on other nodes):"
  for entry in "$LOGS"/*.json; do
    python3 - "$entry" <<'PY' 2>/dev/null
import json, socket, sys
d = json.load(open(sys.argv[1]))
host, pid = d.get("host", "?"), d.get("pid", "?")
here = host == socket.gethostname()
alive = ""
if here:
    try:
        import os; os.kill(int(pid), 0); alive = " ALIVE"
    except Exception:
        alive = " (gone)"
print(f"  {d.get('run','?').split('/')[-1]:<26} pid {pid} on {host}"
      f"{alive}{'' if here else '  [not this node]'}  started {d.get('started','?')}")
PY
  done
fi

# What the newest run has cost so far, from the arms that report cost.
echo
newest=$(ls -dt "$RUNS"/*/ 2>/dev/null | head -1)
if [ -n "$newest" ]; then
  echo "newest run: $(basename "${newest%/}")"
  python3 - "${newest%/}" <<'PY' 2>/dev/null
import json, pathlib, sys

root = pathlib.Path(sys.argv[1])
total = 0.0
for results in sorted(root.glob("*/results.jsonl")):
    cost = tokens = 0.0
    rows = 0
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows += 1
        # Research is billed too — omitting it understated the spend on exactly
        # the arm this script exists to watch.
        cost += sum(float(a.get("cost_usd") or 0)
                    + float(a.get("research_cost_usd") or 0)
                    for a in row.get("attempts") or [])
        tokens += float(row.get("tokens_solve") or 0) + float(row.get("tokens_research") or 0)
    total += cost
    print(f"  {results.parent.name:<18} {rows} task(s)  ${cost:.2f}  "
          f"{tokens/1000:.0f}k tokens")
if total:
    print(f"  {'TOTAL so far':<18}          ${total:.2f}")
    print("  (finished tasks only — a task in flight is not counted yet)")
PY
fi

echo
echo "to stop everything:  $SCRIPTS/kill.sh        (add --dry-run to preview)"
