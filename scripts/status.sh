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
  # From the files the runner writes, not from a walk of the whole run.
  #
  # The walk was `find <run> -type f -newermt`, which on a live run means every
  # file in every checkout and every worktree: 109,000 files and 23 seconds on
  # lustre for one run — so `status.sh` appeared to hang, and appeared to hang
  # worse the more work the run had done. The trace and the results file are
  # touched on every stage and every task, which is the same signal for the
  # price of two stats.
  local run="$1" now last age
  now=$(date +%s)
  last=$(stat -c '%Y' "$run"/*/trace.log "$run"/*/results.jsonl \
                      "$run"/manifest.json 2>/dev/null | sort -rn | head -1)
  [ -z "$last" ] && { echo "idle"; return; }
  age=$(( now - last ))
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

  # How the model endpoint is actually behaving, from the server's own counters.
  #
  # Read rather than probed. A synthetic request measures the probe and adds to
  # the very queue it is trying to describe; llama.cpp already publishes what it
  # has done, so this costs one cheap GET and reports the RUN's traffic instead
  # of its own.
  #
  # `deferred` is the number to watch. Measured live: this server has ONE slot,
  # so requests are strictly serialised — with both arms running, one was always
  # processing and one always deferred, and the arm that looked "idle" for
  # fifteen minutes was waiting its turn. That reads as a broken agent and is
  # nothing of the kind.
  local endpoint
  endpoint=$(python3 -c "
import json
try:
    d = json.load(open('$RUN/manifest.json'))
    # Skipped where the recorded base_url is not the one the arm talks to:
    # Claude Code reaches Anthropic directly and the manifest still carries a
    # gateway URL, so its numbers would describe an endpoint this run never used.
    print('' if d.get('provider') == 'anthropic' else (d.get('base_url') or ''))
except Exception:
    print('')" 2>/dev/null)
  if [ -n "$endpoint" ]; then
    python3 - "$endpoint" "$RUN" <<'PY' 2>/dev/null
import json
import os
import sys
import time
import urllib.error
import urllib.request

base, run = sys.argv[1].rstrip("/"), sys.argv[2]
# The metrics live on the server root, not under the API prefix the model is
# served from.
root = base[:-3].rstrip("/") if base.endswith("/v1") else base


def fetch(path, timeout=10):
    request = urllib.request.Request(f"{root}{path}")
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        request.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


try:
    raw = fetch("/metrics")
except (urllib.error.URLError, OSError) as exc:
    code = getattr(exc, "code", None)
    if code == 404:
        # Not every endpoint publishes metrics; that is not a fault.
        raise SystemExit
    why = ("needs OPENAI_API_KEY" if code in (401, 403)
           else f"{type(exc).__name__}: {exc}")
    print(f"  endpoint: {base} — {why}")
    raise SystemExit

metric = {}
for line in raw.splitlines():
    if line.startswith("#") or " " not in line:
        continue
    name, _, value = line.partition(" ")
    try:
        metric[name] = float(value)
    except ValueError:
        continue


def get(name, default=0.0):
    return metric.get(f"llamacpp:{name}", default)


busy = get("requests_processing")
deferred = get("requests_deferred")
slots = ""
try:
    seen = json.loads(fetch("/slots"))
    if isinstance(seen, list):
        slots = f"/{len(seen)}"
except Exception:
    pass                       # the slot list is a nicety; the counters are not

queue = ("  ** ONE slot — requests are serialised, so an arm that looks idle "
         "is queued" if slots == "/1" and deferred
         else "  ** requests are queueing" if deferred else "")
print(f"  endpoint: {base}")
print(f"            processing {busy:.0f}{slots} slot(s), {deferred:.0f} "
      f"deferred{queue}")
print(f"            prompt {get('prompt_tokens_seconds'):,.0f} tok/s   "
      f"generate {get('predicted_tokens_seconds'):,.0f} tok/s")

# Throughput since the previous look, which is the only figure that describes
# THIS run rather than everything the server has done since it booted.
now = time.time()
sample = {"at": now, "prompt": get("prompt_tokens_total"),
          "predicted": get("tokens_predicted_total")}
path = os.path.join(run, ".endpoint-sample.json")
try:
    with open(path) as handle:
        last = json.load(handle)
    gap = now - float(last["at"])
    if 5 < gap < 3600:
        did_prompt = sample["prompt"] - float(last["prompt"])
        did_gen = sample["predicted"] - float(last["predicted"])
        print(f"            since last check ({gap / 60:.0f} min): "
              f"{did_prompt:,.0f} prompt + {did_gen:,.0f} generated tokens "
              f"({did_gen / gap:,.1f} tok/s sustained)")
except (OSError, ValueError, KeyError):
    pass
try:
    with open(path, "w") as handle:
        json.dump(sample, handle)
except OSError:
    pass

served = get("prompt_seconds_total") + get("tokens_predicted_seconds_total")
print(f"            server total: {get('prompt_tokens_total'):,.0f} prompt + "
      f"{get('tokens_predicted_total'):,.0f} generated tokens in "
      f"{served / 60:.0f} min of compute")
PY
  fi

  local arm name done_n total live newest
  for arm in "$RUN"/*/; do
    name=$(basename "$arm")
    [ -d "$arm/tasks" ] || continue
    # Counted from the per-task result files: each is written by the one thread
    # that owns that directory, so the count cannot lag behind reality the way
    # a shared aggregate can when several tasks finish at once.
    done_n=$(ls "$arm"/tasks/*/result.json 2>/dev/null | wc -l)
    if [ "$done_n" -eq 0 ]; then
      # Fall back to the promotion marker for runs without result files.
      done_n=$(grep -l "] promoted" "$arm"/tasks/*/trace.log 2>/dev/null | wc -l)
    fi
    total=$(ls -d "$arm"/tasks/*/ 2>/dev/null | wc -l)
    # Passes, read from the same per-task files as the finished count. Read out
    # of `results.jsonl` this would lag: the aggregate is appended under a lock,
    # so a task that has already written its own result can still be missing
    # from it, and a header reading "3 finished, 1/2 passed" looks like a lost
    # result rather than a slow append.
    local passed
    passed=$(python3 - "$arm" <<'COUNT' 2>/dev/null
import json, sys
from pathlib import Path

n = 0
for path in sorted(Path(sys.argv[1], "tasks").glob("*/result.json")):
    try:
        n += 1 if json.loads(path.read_text()).get("resolved") else 0
    except Exception:
        # A result being written right now is worth skipping, not crashing on.
        continue
print(n)
COUNT
)
    echo
    echo "=== $name — ${passed:-0}/$done_n passed, $total started ==="

    python3 - "$arm/results.jsonl" <<'PY' 2>/dev/null
import json, sys
from collections import OrderedDict

try:
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
except OSError:
    rows = []

# Long stage names push the numbers off the line.
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
            g["starved"] = g.get("starved", 0) + int(d.get("starved") or 0)
    if grouped:
        parts = []
        for name, g in grouped.items():
            label = SHORT.get(name, name)
            cut = f" !{g['cut']}cut" if g["cut"] else ""
            starved = f" !{g['starved']}starved" if g.get("starved") else ""
            parts.append(f"{label} {g['n']}x max {g['max']:.0f}s{cut}{starved}"
                         if g["n"] > 1
                         else f"{label} {g['s']:.0f}s{cut}{starved}")
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

    # Every task in flight, one line each, from its own log.
    #
    # With tasks running concurrently there is no single "in flight" task, and
    # showing the most recently touched one reported whichever happened to
    # write last — a display that changed every second and described one sixth
    # of the work. Each task writes its own trace now, so this is a tail per
    # file rather than a parse of six interleaved conversations.
    live_n=$(( total - done_n ))
    if [ "$live_n" -gt 0 ]; then
      echo "  in flight: $live_n of $total"
      now=$(date +%s)
      for task_dir in "$arm"/tasks/*/; do
        [ -f "$task_dir/trace.log" ] || continue
        # A task with results already recorded is finished, not in flight.
        name=$(basename "$task_dir")
        [ -f "$task_dir/result.json" ] && continue
        # A task whose last act was promoting what it learned is finished, even
        # when no result file exists — a run started before those were written,
        # or one whose results were batched to the end, would otherwise show
        # three finished tasks sitting "idle" for the rest of the run.
        case "$(grep "\] " "$task_dir/trace.log" 2>/dev/null | tail -1)" in
          *"] promoted"*|*"] task-done"*) continue ;;
        esac

        # Which try this is. A task on try 2 has already produced a patch and
        # had it judged wrong, so the stage names mean something different:
        # `diagnose` on try 1 is impossible, and `survey` on try 3 would be a
        # bug. Without it the line reads as first-time work whatever happened.
        tries=$(ls -d "$task_dir"/attempt-*/ 2>/dev/null | wc -l)
        [ "$tries" -lt 1 ] && tries=1
        try_mark=""
        [ "$tries" -gt 1 ] && try_mark="try $tries "

        # The last line that IS an event, not the last line in the file.
        #
        # An event with details writes them as indented continuation lines, so
        # `tail -1` returned "budget 1800s" — no timestamp, no kind — and the
        # display showed an empty stage with the detail as its message. The
        # marker is the `[arm:pid:task]` prefix every real event carries.
        last=$(grep "\] " "$task_dir/trace.log" 2>/dev/null | tail -1)
        touched=$(stat -c '%Y' "$task_dir/trace.log" 2>/dev/null || echo "$now")
        idle=$(( now - touched ))
        # kind and summary, from the line the task last wrote.
        rest=${last#*] }
        kind=${rest%% *}
        # Eighty characters, because that is what the describer writes. Cut at
        # 46 the line read "searching the source for def load_dot" — the width
        # threw away the half of the sentence that says what is being looked
        # for, which is the only part that distinguishes one line from the next.
        what=$(echo "${rest#"$kind"}" | cut -c1-46)
        mark=""
        [ "$idle" -gt 300 ] && mark="  ** idle"
        printf "    %-26s %-7s%-18s %-46s %4ss ago%s\n" \
               "${name#*-}" "$try_mark" "$kind" "$what" "$idle" "$mark"
      done
      echo "    follow one:  tail -f $arm/tasks/<task>/trace.log"
    fi

    if [ -d "$arm/store/.phronix/skills" ]; then
      have=$(ls "$arm/store/.phronix/skills" | wc -l)
      tools=$(ls "$arm/store/.phronix/capabilities"/*.py 2>/dev/null | wc -l)
      echo "  store: $have skill(s) — seeded $BASELINE, learned $(( have - BASELINE ))"\
"   |   $tools tool(s)"
      echo "  retrievals: $(cat "$arm"/tasks/*/retrievals.jsonl 2>/dev/null | wc -l)"

      # What was learned, by name. A count says the loop ran; the names say
      # what it produced, and a name is what makes a claim checkable — "learned
      # 3" has been true of runs that wrote three fragments of one subject.
      BUNDLED=/usr/WS2/haridev/phronix/src/phronix/.agents/skills
      for skill in "$arm/store/.phronix/skills"/*/; do
        name=$(basename "$skill")
        [ -d "$BUNDLED/$name" ] && continue
        echo "    + skill $name"
      done
      for tool in "$arm/store/.phronix/capabilities"/*.py; do
        [ -f "$tool" ] || continue
        base=$(basename "$tool" .py)
        case "$base" in probe_*) kind="method" ;; *) kind="solution" ;; esac
        echo "    + tool  $base ($kind)"
      done
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
