#!/bin/bash
# What each task actually USED out of the store, learned or otherwise.
#
#   reuse.sh                 # the most recent run
#   reuse.sh <run-dir>
#
# The question this answers is not "did the store grow" — a run that writes
# forty skills nobody ever loads has grown and learned nothing. It is "did a
# task load something a previous task wrote, and did it load it while SOLVING
# rather than while looking around".
#
# Three columns, and only the third is the benchmark's actual claim:
#
#   loaded      every skill the task pulled in, any phase
#   learned     of those, the ones written by a run rather than shipped
#   in solve    of those, the ones loaded during the attempt itself
#
# A learned skill loaded only during research is weaker evidence than it looks:
# research can read a skill and then hand the attempt a plan that never mentions
# it, and the attempt then solves the task without the knowledge ever reaching
# it. That distinction is why `phase` is recorded at retrieval time.
set -uo pipefail

BENCH=/p/lustre5/haridev/phronix-bench
RUN="${1:-$(ls -dt "$BENCH"/runs/*/ 2>/dev/null | head -1)}"
RUN="${RUN%/}"

[ -d "$RUN" ] || { echo "no run at $RUN" >&2; exit 2; }
echo "run: $RUN"

for arm in "$RUN"/*/; do
  [ -d "$arm/tasks" ] || continue
  echo
  echo "=== $(basename "$arm") ==="
  python3 - "$arm" <<'PY'
import json
import sys
from pathlib import Path

arm = Path(sys.argv[1])
rows = []
learned_all, capability_all = set(), set()

for task_dir in sorted(arm.glob("tasks/*/")):
    log = task_dir / "retrievals.jsonl"
    loaded, learned, in_solve, searches, empty = set(), set(), set(), 0, 0
    if log.is_file():
        for line in log.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            names = rec.get("skills") or []
            if rec.get("kind") == "search":
                searches += 1
                if not names:
                    empty += 1
            loaded.update(names)
            # `learned` is recorded at retrieval time by layer, because a name
            # alone cannot say who wrote it: a learned skill about flask is
            # named for flask exactly like a shipped one would be.
            mine = set(rec.get("learned") or [])
            learned.update(mine)
            if rec.get("phase") == "solve":
                in_solve.update(mine)

    # Capabilities are tools, so their use is a tool call in the transcript
    # rather than a retrieval. A learned tool that is never called is the same
    # kind of nothing as a learned skill that is never loaded.
    called = set()
    for transcript in task_dir.glob("attempt-*/*.jsonl"):
        for line in transcript.read_text(errors="replace").splitlines():
            if "mcp__phronix__probe_" not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = str(block.get("name") or "")
                if "probe_" in name:
                    called.add(name.split("__")[-1])

    learned_all |= learned
    capability_all |= called
    rows.append((task_dir.name[4:], len(loaded), len(learned), len(in_solve),
                 searches, empty, sorted(in_solve), sorted(called)))

if not rows:
    print("  no tasks yet")
    raise SystemExit

print(f"  {'task':<30} {'loaded':>6} {'learned':>7} {'in solve':>8} "
      f"{'searches':>8} {'empty':>6}")
for name, loaded, learned, solve, searches, empty, which, called in rows:
    print(f"  {name:<30} {loaded:>6} {learned:>7} {solve:>8} "
          f"{searches:>8} {empty:>6}")
    for skill in which:
        print(f"      used while solving: {skill}")
    for tool in called:
        print(f"      called learned tool: {tool}")

solved_with = sum(1 for r in rows if r[3])
print(f"  -- {solved_with}/{len(rows)} task(s) used a LEARNED skill while solving")
if learned_all:
    print(f"  -- learned skills touched at all: {', '.join(sorted(learned_all))}")
if capability_all:
    print(f"  -- learned tools called: {', '.join(sorted(capability_all))}")

# An empty search is a real answer, not a broken pipe: a store whose only skills
# are about the framework returns nothing for every domain query, which is the
# expected early state. Worth printing so it is never read as a wiring fault.
blank = sum(r[5] for r in rows)
if blank:
    print(f"  -- {blank} search(es) matched nothing (expected while the store "
          f"is young; not a wiring fault)")
PY
done
