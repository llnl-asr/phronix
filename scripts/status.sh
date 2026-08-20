#!/bin/bash
# How runs are going.  Usage:
#
#   status.sh                 full detail for the newest run (the default)
#   status.sh <run>           full detail for that run (name or path)
#   status.sh --all           every run, one line each, newest first
#   status.sh --list [N]      just the names of the last N runs (default 5)
#
# The runner prints one line per COMPLETED task and an agent's transcript is
# only written when it exits, so a run in progress looks identical to a hung one
# from the terminal. This reads the artifacts on disk instead.
set -uo pipefail

BENCH=/p/lustre5/haridev/phronix-bench
RUNS="$BENCH/runs"
SCRIPTS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# The seeded baseline is read from the framework, not hardcoded.
#
# It was hardcoded as 12, and then the framework gained a skill: both arms
# suddenly showed 13 and the line read as if the BASELINE had learned something,
# which it cannot do. A constant that tracks a number in another repository is a
# constant that will be wrong and will be believed.
BASELINE=$(ls /usr/WS2/haridev/phronix/src/phronix/.agents/skills 2>/dev/null | wc -l)
BASELINE=${BASELINE:-0}

resolve() {   # resolve <name-or-path> -> absolute run dir
  local want="$1"
  [ -d "$want" ] && { echo "${want%/}"; return; }
  [ -d "$RUNS/$want" ] && { echo "$RUNS/$want"; return; }
  return 1
}

liveness() {  # liveness <run-dir> -> one word plus age
  local run="$1" now last age
  now=$(date +%s)
  last=$(find "$run" -type f -newermt '-2 hours' -printf '%T@\n' 2>/dev/null \
         | sort -rn | head -1)
  [ -z "$last" ] && { echo "idle"; return; }
  age=$(( now - ${last%.*} ))
  if [ "$age" -lt 180 ]; then echo "ALIVE ${age}s"; else echo "stopped ${age}s"; fi
}

summarise() { # one line per arm, for the overview
  python3 - "$1" <<'PY' 2>/dev/null
import json, pathlib, sys

run = pathlib.Path(sys.argv[1])
for results in sorted(run.glob("*/results.jsonl")):
    rows, passed, cost, tokens = 0, 0, 0.0, 0
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows += 1
        passed += 1 if row.get("resolved") else 0
        cost += sum(float(a.get("cost_usd") or 0) for a in row.get("attempts") or [])
        tokens += int(row.get("tokens_solve") or 0) + int(row.get("tokens_research") or 0)
    started = len(list((results.parent / "tasks").glob("*"))) if (results.parent / "tasks").is_dir() else 0
    money = f" ${cost:.2f}" if cost else ""
    print(f"      {results.parent.name:<18} {passed}/{rows} passed"
          f"  ({started} started)  {tokens/1000:.0f}k tok{money}")
PY
}

overview() {
  local run state
  echo "runs in $RUNS (newest first)"
  echo
  for run in $(ls -dt "$RUNS"/*/ 2>/dev/null); do
    run="${run%/}"
    [ -d "$run" ] || continue
    state=$(liveness "$run")
    printf "  %-26s %s\n" "$(basename "$run")" "$state"
    summarise "$run"
  done
  echo
  echo "detail:  $SCRIPTS/status.sh <run>   |   newest:  $SCRIPTS/status.sh"
}

detail() {
  local RUN="$1"
  echo "run: $RUN"
  echo "this node: $(hostname)   state: $(liveness "$RUN")"

  # What this run was configured to measure. The model above all: two runs are
  # only comparable if they asked the same model the same questions.
  [ -f "$RUN/manifest.json" ] && python3 -c "
import json
d = json.load(open('$RUN/manifest.json'))
print(f\"  model: {d.get('model','?')} ({d.get('provider','?')})   node: {d.get('node') or '?'}\"
      f\"   mode: {'fresh' if d.get('fresh') else 'reuse'}\"
      f\"{' research-on-retry' if d.get('research_on_retry') else ''}\"
      f\"   tries<={d.get('max_tries','?')}\")" 2>/dev/null

  # Where it was launched from, if the launcher recorded it. Survives the
  # allocation the run was started in, which pgrep does not.
  local log="/usr/WS2/haridev/phronix/logs/$(basename "$RUN").json"
  [ -f "$log" ] && python3 -c "
import json,sys
d=json.load(open('$log'))
print(f\"  launched: pid {d.get('pid')} on {d.get('host')} at {d.get('started')}\")" 2>/dev/null

  local arm name done_n total live newest
  for arm in "$RUN"/*/; do
    name=$(basename "$arm")
    [ -d "$arm/tasks" ] || continue
    done_n=$(grep -c . "$arm/results.jsonl" 2>/dev/null || echo 0)
    total=$(ls -d "$arm"/tasks/*/ 2>/dev/null | wc -l)
    echo
    echo "=== $name — $done_n finished, $total started ==="

    python3 - "$arm/results.jsonl" <<'PY' 2>/dev/null
import json, sys
from collections import OrderedDict

try:
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
except OSError:
    rows = []

SHORT = {"execution-plan": "exec-plan", "aspect-record": "record",
         "aspect-recheck": "recheck"}


def short(n):
    """A token count at a glance: 940, 12.5k, 1.6M."""
    n = max(0, int(n))
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    # A decimal on six figures is precision nobody uses: 242.6k reads slower
    # than 243k and says nothing more.
    if n >= 100_000:
        return f"{n / 1000:.0f}k"
    if n >= 1_000:
        return f"{n / 1000:.1f}k"
    return str(n)


def tokens(fresh, total):
    """Generated over total, as one column: `12.5k/1.6M`.

    Both numbers matter and neither is the other's unit. The first is what the
    model wrote; the second is everything it was charged for, which is mostly
    the same context re-counted on every api call — so it scales with step
    count while the first scales with work. Spelled out (`12,535 gen / 1.6M`)
    the pair was wider than the columns around it and read as a sentence; as a
    ratio it reads as one quantity, which is how it is used.
    """
    return f"{short(fresh) + '/' + short(total):>12}"

totals = {"solve": 0, "research": 0, "learn": 0, "st": 0.0, "rt": 0.0,
          "cost": 0.0, "rcost": 0.0, "fresh": 0, "fresh_research": 0}

for r in rows:
    attempts = r.get("attempts") or []
    steps = sum(int(a.get("steps") or 0) for a in attempts)
    passes = (r.get("research") or {}).get("passes_detail") or []
    research_t = sum(float(p.get("elapsed_s") or 0) for p in passes)

    # Research runs INSIDE the attempt's wall clock — it needs the exported
    # checkout — so wall_s alone reported a six-step attempt as taking 1020s
    # when 922s of that was research. Subtract it, and learning with it: the
    # number next to steps= should be the agent working on the task, which is
    # the only thing the baseline's time is comparable to.
    solve_t = sum(max(0.0, float(a.get("wall_s") or 0)
                      - float(a.get("research_s") or 0)
                      - float(a.get("learn_s") or 0)) for a in attempts)
    cost = sum(float(a.get("cost_usd") or 0) for a in attempts)
    research_cost = sum(float(a.get("research_cost_usd") or 0) for a in attempts)

    solve = int(r.get("tokens_solve") or 0)
    research = int(r.get("tokens_research") or 0)
    learn = int(r.get("tokens_learn") or 0)

    # Generated tokens, apart from cache reads.
    #
    # A cache read is re-counted on EVERY api call, so the same system prompt
    # and context are charged once per step: one task showed tok=4,280,097 of
    # which 4,256,333 were cache reads and 23,618 were actually generated. The
    # big number reads as "this attempt did an enormous amount of work" when it
    # says the opposite — a short, specific attempt that re-read its context 72
    # times. Both are real, they just answer different questions, so both are
    # shown and the one about work comes first.
    fresh = sum(int(a.get("tokens_input") or 0) + int(a.get("tokens_output") or 0)
                for a in attempts)
    fresh_research = sum(int(p.get("tokens_input") or 0)
                         + int(p.get("tokens_output") or 0) for p in passes)
    for key, value in (("solve", solve), ("research", research), ("learn", learn),
                       ("st", solve_t), ("rt", research_t), ("cost", cost),
                       ("rcost", research_cost), ("fresh", fresh),
                       ("fresh_research", fresh_research)):
        totals[key] += value

    tries = int(r.get("tries") or 1)
    retried = f"tries={tries} " if tries > 1 else ""
    money = f" ${cost:.2f}" if cost else ""
    line = (f"  {'PASS' if r.get('resolved') else 'fail'}  {r['instance_id']:<28} "
            f"{retried}steps={steps:<3} tok={tokens(fresh, solve)} "
            f"time={solve_t:>5.0f}s{money}")
    if research or learn:
        line += (f"   research tok={tokens(fresh_research, research)} "
                 f"time={research_t:>5.0f}s"
                 + (f" ${research_cost:.2f}" if research_cost else "")
                 + (f" learn tok={learn:,}" if learn else ""))
    print(line)

    # One line per try, because a task's story is the progression.
    #
    # The totals above answer "what did this task cost"; they cannot answer
    # "did the retry help", which is the question a retry exists to raise. A
    # try that spent 900s researching and then solved in 6 steps is a different
    # event from one that researched for 90s and flailed for 40 steps, and the
    # sum of the two looks like neither.
    if len(attempts) > 1 or passes:
        by_attempt = {}
        for p in passes:
            slot = by_attempt.setdefault(int(p.get("attempt") or 1),
                                         {"tok": 0, "fresh": 0, "s": 0.0, "cost": 0.0})
            slot["tok"] += (int(p.get("tokens_input") or 0)
                            + int(p.get("tokens_output") or 0)
                            + int(p.get("tokens_cache") or 0))
            slot["fresh"] += (int(p.get("tokens_input") or 0)
                              + int(p.get("tokens_output") or 0))
            slot["s"] += float(p.get("elapsed_s") or 0)
            slot["cost"] += float(p.get("cost_usd") or 0)

        for a in attempts:
            index = int(a.get("index") or 0)
            # A revision pass runs under the NEXT index, so a try owns its own
            # research plus any revision that was made for it.
            research_here = by_attempt.get(index, {"tok": 0, "fresh": 0,
                                                   "s": 0.0, "cost": 0.0})
            a_fresh = int(a.get("tokens_input") or 0) + int(a.get("tokens_output") or 0)
            a_tok = a_fresh + int(a.get("tokens_cache") or 0)
            a_time = max(0.0, float(a.get("wall_s") or 0)
                         - float(a.get("research_s") or 0)
                         - float(a.get("learn_s") or 0))
            outcome = ("PASS" if a.get("resolved")
                       else (str(a.get("error") or "")[:28] or "fail"))
            # One number per phase here, not the generated/total ratio: these
            # lines exist to show the PROGRESSION across tries, and a ratio per
            # cell turns a comparison of six numbers into one of twelve.
            head = f"        try{index} {outcome:<10}"
            if research_here["s"] or research_here["tok"]:
                head += (f" research {short(research_here['tok']):>6}"
                         f" {research_here['s']:>5.0f}s"
                         + (f" ${research_here['cost']:.2f}"
                            if research_here["cost"] else ""))
            head += (f"   task steps={int(a.get('steps') or 0):<3}"
                     f" {short(a_tok):>6} {a_time:>5.0f}s"
                     + (f" ${float(a.get('cost_usd') or 0):.2f}"
                        if a.get("cost_usd") else ""))
            print(head)

    grouped = OrderedDict()
    for p in passes:
        for d in p.get("stage_detail") or []:
            key = str(d.get("stage", "?")).split(":", 1)[0]
            g = grouped.setdefault(key, {"n": 0, "s": 0.0, "max": 0.0, "cut": 0})
            g["n"] += 1
            g["s"] += float(d.get("elapsed_s") or 0)
            # Parallel stages cost their SLOWEST member, not the sum.
            g["max"] = max(g["max"], float(d.get("elapsed_s") or 0))
            g["cut"] += 1 if d.get("truncated") else 0
    if grouped:
        parts = []
        for name, g in grouped.items():
            label = SHORT.get(name, name)
            cut = f" !{g['cut']}cut" if g["cut"] else ""
            parts.append(f"{label} {g['n']}x max {g['max']:.0f}s{cut}" if g["n"] > 1
                         else f"{label} {g['s']:.0f}s{cut}")
        print("        research: " + " | ".join(parts))

if rows:
    grand = totals["solve"] + totals["research"] + totals["learn"]
    passed = sum(1 for r in rows if r.get("resolved"))
    money = f" ${totals['cost']:.2f}" if totals["cost"] else ""
    line = (f"  ==    {'TOTAL ' + str(passed) + '/' + str(len(rows)) + ' passed':<28} "
            f"tok={tokens(totals['fresh'], totals['solve'])} "
            f"time={totals['st']:>5.0f}s{money}")
    if totals["research"] or totals["learn"]:
        share = 100.0 * (totals["research"] + totals["learn"]) / grand if grand else 0
        line += (f"   research tok={tokens(totals['fresh_research'], totals['research'])} "
                 f"time={totals['rt']:>5.0f}s"
                 + (f" ${totals['rcost']:.2f}" if totals["rcost"] else "")
                 + f"  ({share:.0f}% of tokens on research)")
    print(line)
PY

    live=$(ls -dt "$arm"/tasks/*/ 2>/dev/null | head -1)
    if [ -n "$live" ] && [ "$done_n" -lt "$total" ]; then
      newest=$(find "$live" -type f -printf '%TH:%TM:%TS %p\n' 2>/dev/null | sort -rn | head -1)
      echo "  in flight: $(basename "$live")"
      echo "    last write: ${newest%% *}  ($(basename "${newest#* }"))"

      # Attempt outcomes as they happen. results.jsonl is only appended once the
      # WHOLE task is done — after the attempt passes, the learning pass runs and
      # the store is promoted — so for a minute or so the trace says PASS and the
      # table above still says nothing happened.
      tail -400 "$arm/trace.log" 2>/dev/null \
        | grep -E "try [0-9]+: (PASS|FAILED)|verdict: " | tail -3 | sed "s/^/    /"

      # Live stage timing, from the trace: research.json is only written when the
      # task ends, so the finished-task breakdown is empty for the task you are
      # actually watching.
      python3 - "$arm/trace.log" <<'PY' 2>/dev/null
import re, sys
from collections import OrderedDict

STAMP = re.compile(r"^(\d\d):(\d\d):(\d\d)\s")
BRACKET = re.compile(r"\[([^\]]+)\]")
# Only real stage names: taking any bracket that was not the [arm:pid] prefix
# also matched the pass summary's "[757.6s]", which appeared as a stage called
# "757.6s" that had been running for 0 seconds.
STAGE = re.compile(r"^(survey|plan|collect|propose|diagnose|tune:.+|execution-plan"
                   r"|aspect:.+|evaluate:.+|aspect-record:.+)$")

def seconds(m):
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

def stage_of(line):
    for name in BRACKET.findall(line):
        if STAGE.match(name):
            return name
    return None

stages, cut = OrderedDict(), set()
last_stage = None
research_is_live = False
try:
    lines = open(sys.argv[1], errors="replace").read().splitlines()
except OSError:
    lines = []

# Anchor on where the last survey BEGAN, not the last survey line: taking the
# last one truncated the survey to its final instant and reported it as 0s.
start, previous_was_survey = 0, False
for i, line in enumerate(lines):
    is_survey = "[survey]" in line
    if is_survey and not previous_was_survey:
        start = i
    if "research" in line:
        previous_was_survey = is_survey

for line in lines[start:]:
    stamp = STAMP.match(line)
    if not stamp or "research" not in line:
        continue
    name = stage_of(line)
    if not name:
        continue
    t = seconds(stamp)
    row = stages.setdefault(name, [t, t])
    row[1] = t
    last_stage = name
    if "TRUNCATED" in line:
        cut.add(name)

for line in reversed(lines):
    if STAMP.match(line) and "] " in line:
        research_is_live = "research" in line.split("] ", 1)[1][:12]
        break

if stages:
    print("    current research pass, stage by stage:")
    for name, (first, last) in stages.items():
        held = last - first
        mark = "  ** CUT OFF at budget" if name in cut else ""
        live = "  <- running" if (name == last_stage and research_is_live) else ""
        print(f"      {name:<34} {held:>5}s{live}{mark}")
    spans = list(stages.values())
    elapsed = max(s[1] for s in spans) - min(s[0] for s in spans)
    charged = sum(s[1] - s[0] for s in spans)
    label = "pass so far" if research_is_live else "pass complete"
    print(f"      {label:<34} {elapsed:>5}s wall, {charged}s across stages "
          f"({'aspects and evaluators overlap' if charged > elapsed else 'serial'})")
    if not research_is_live:
        print(f"      {'':<34}       research has finished; the attempt is running")
PY
    fi

    if [ -d "$arm/store/.phronix/skills" ]; then
      have=$(ls "$arm/store/.phronix/skills" | wc -l)
      echo "  skills in store: $have (seeded $BASELINE, learned $(( have - BASELINE )))"
      echo "  retrievals: $(cat "$arm"/tasks/*/retrievals.jsonl 2>/dev/null | wc -l)"
    fi
    [ -f "$arm/trace.log" ] && echo "  trace: $arm/trace.log"
  done

  # What the whole run has cost, both arms together. The per-arm totals above
  # answer "which arm is expensive"; this answers "what am I spending".
  echo
  python3 - "$RUN" <<'PY' 2>/dev/null
import json, pathlib, sys

root = pathlib.Path(sys.argv[1])
grand, per_task, unpriced = 0.0, [], 0
for results in sorted(root.glob("*/results.jsonl")):
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        attempts = row.get("attempts") or []
        # Task and research billed separately: research is a real charge on the
        # account, and lumping it into one number cannot say whether phronix is
        # expensive because it researches or because it solves slowly.
        task_cost = sum(float(a.get("cost_usd") or 0) for a in attempts)
        res_cost = sum(float(a.get("research_cost_usd") or 0) for a in attempts)
        if not (task_cost or res_cost):
            unpriced += 1
        grand += task_cost + res_cost
        per_task.append((results.parent.name, row.get("instance_id", "?"),
                         task_cost, res_cost))

if per_task:
    print("=== cost ===")
    print(f"  {'arm':<16} {'task':<30} {'task $':>8} {'research $':>11} {'total $':>9}")
    for arm, task, task_cost, res_cost in per_task:
        print(f"  {arm:<16} {task:<30} {task_cost:>8.2f} {res_cost:>11.2f} "
              f"{task_cost + res_cost:>9.2f}")
    tt = sum(p[2] for p in per_task)
    rr = sum(p[3] for p in per_task)
    print(f"  {'TOTAL':<16} {str(len(per_task)) + ' finished task(s)':<30} "
          f"{tt:>8.2f} {rr:>11.2f} {grand:>9.2f}")
    # A task still in flight has no row yet, so this is a floor, not the bill.
    print("  (finished tasks only — a task in flight is not counted yet)")
    if unpriced:
        print(f"  ({unpriced} task(s) reported no cost — that arm's harness "
              f"does not price its calls)")
PY
}

case "${1:-}" in
  --list)
    ls -dt "$RUNS"/*/ 2>/dev/null | head -"${2:-5}" | while read -r run; do
      printf "  %-26s %s\n" "$(basename "${run%/}")" "$(liveness "${run%/}")"
    done
    ;;
  --last|"")
    # The default. Watching a run is what this is for, and that is almost always
    # the newest one; the overview is a thing you ask for.
    detail "$(ls -dt "$RUNS"/*/ 2>/dev/null | head -1 | sed 's:/$::')"
    ;;
  --all)
    overview
    ;;
  *)
    target=$(resolve "$1") || { echo "no such run: $1" >&2; exit 1; }
    detail "$target"
    ;;
esac
