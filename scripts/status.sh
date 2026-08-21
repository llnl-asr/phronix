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

# One way to write a duration, everywhere.
#
# Raw seconds are unreadable past a couple of minutes: "time= 1987s" and
# "stopped 15080s" both require arithmetic to mean anything, and the second is
# four hours. Same shape as the in-flight elapsed column: 45s, 12m30s, 2h05m.
human() {   # human <seconds> -> 45s | 12m30s | 2h05m
  local s=${1%.*}
  [ -z "$s" ] && { echo "-"; return; }
  if   [ "$s" -ge 3600 ]; then printf '%dh%02dm' $((s/3600)) $((s%3600/60))
  elif [ "$s" -ge 60 ];   then printf '%dm%02ds' $((s/60)) $((s%60))
  else                         printf '%ds' "$s"
  fi
}

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
  if [ "$age" -lt 180 ]; then echo "ALIVE $(human "$age")"
  else echo "stopped $(human "$age") ago"; fi
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

overall() {   # overall <run-dir> -> how fast the whole run is going
  # Rate for the run as a whole. What was LEARNED is reported at the end,
  # next to what was added, so the two halves of the same question — what
  # got written, and whether anything read it — are read together.
  echo
  python3 - "$1" <<'PY' 2>/dev/null
import json, pathlib, sys, time, collections
from datetime import datetime

def human(seconds):
    """45s | 12m30s | 2h05m — the same shape the shell side writes."""
    s = int(seconds or 0)
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


root = pathlib.Path(sys.argv[1])

# ---- throughput ----------------------------------------------------------
# Wall time is measured from the earliest thing the run wrote to the latest,
# not from now: a finished run must not keep inflating its own denominator.
#
# The start comes from the manifest, which the runner writes once. It was
# taken from the minimum file ctime, and on Lustre ctime is the inode-change
# time and moves on every append — so a FINISHED run, whose files had all been
# touched again, reported a wall of 32,245 minutes and 161,226 s per task.
stamps = [p.stat().st_mtime for p in root.rglob("*") if p.is_file()]
start = 0.0
try:
    created = json.loads((root / "manifest.json").read_text())["created_at"]
    start = datetime.fromisoformat(created).timestamp()
except Exception:
    # No manifest: fall back to the oldest mtime, which at least cannot be
    # younger than the run.
    start = min(stamps, default=0)
wall = max(stamps, default=0) - start
done = attempts = prompt = generated = 0
resolved = 0
for results in sorted(root.glob("*/results.jsonl")):
    for line in results.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        done += 1
        resolved += 1 if row.get("resolved") else 0
        for a in row.get("attempts") or []:
            attempts += 1
            prompt += int(a.get("tokens_input") or 0)
            generated += int(a.get("tokens_output") or 0)

# ---- what the agents are actually DOING, per second ----------------------
# A task is not the unit of work here. One task is minutes of an agent reading
# files, running commands and editing — and a run that finishes no tasks at all
# can still be working hard or barely moving. The rate that says which is the
# rate of individual agent actions: tool calls made, model turns completed.
tools_used = collections.Counter()
tool_calls = 0
# By message id, not by event: a streamed assistant message arrives as several
# events carrying the SAME id, and counting events said 714 turns where there
# were a few hundred. The id is the unit the model actually produced.
turn_ids = set()
# Per-agent time, so the run-wide rate can be divided into "how fast is one
# agent" and "how many are running". A slow run means one of those two things
# and the fix is different for each: a slow agent is a model/harness problem,
# too few agents is a concurrency problem.
#
# From the transcript's own timestamps, not the file's. On lustre st_ctime is
# the inode-change time and moves on every append, so mtime - ctime is ~0 and
# the whole per-agent rate silently vanished.
agent_seconds = 0.0
for tr in root.glob("*/tasks/*/attempt-*/*.jsonl"):
    stamps_here = []
    for line in tr.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        when = event.get("timestamp")
        if isinstance(when, str):
            try:
                stamps_here.append(
                    datetime.fromisoformat(when.replace("Z", "+00:00")).timestamp())
            except ValueError:
                pass
        message = event.get("message") or {}
        if message.get("role") == "assistant":
            turn_ids.add((tr.parent, message.get("id") or id(event)))
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_calls += 1
                name = block.get("name") or "?"
                # The phronix tools are the interesting group, not fifteen
                # separate rows crowding out Bash and Read.
                tools_used["mcp__phronix__*" if name.startswith("mcp__phronix__")
                           else name] += 1
    if len(stamps_here) > 1:
        agent_seconds += max(stamps_here) - min(stamps_here)

turns = len(turn_ids)
if wall > 0:
    actions = tool_calls + turns
    print("=== throughput ===")
    print(f"  wall {human(wall)}   {done} task(s) finished, "
          f"{resolved} resolved, {attempts} attempt(s)")
    print(f"  {actions/wall:.2f} agent action/s   "
          f"({tool_calls} tool call(s) at {tool_calls/wall:.2f}/s, "
          f"{turns} model turn(s) at {turns/wall:.2f}/s)")
    if agent_seconds > 0:
        # The two halves of the run-wide rate. Per-agent says how fast one
        # agent moves; concurrency says how many were moving at once. Their
        # product is the line above.
        print(f"  {actions/agent_seconds:.2f} action/s PER AGENT   x "
              f"{agent_seconds/wall:.1f} agent(s) in flight on average   "
              f"= {actions/wall:.2f}/s")
        print(f"  one action every {agent_seconds/max(actions,1):.1f}s "
              f"for a single agent")
    if tools_used:
        top = "  ".join(f"{name} {n}" for name, n in tools_used.most_common(6))
        print(f"  what they do: {top}")
    if done:
        print(f"  {human(wall/done)} per finished task   "
              f"{actions/done:.0f} action(s) per task")
    if generated:
        print(f"  {generated/wall:.0f} generated tok/s over the whole run   "
              f"prompt:generated {prompt/max(generated,1):.0f}:1")
        # A high ratio means the fleet spends its time re-reading context
        # rather than producing. That is a prompt-cache question, not a
        # model-speed one.

PY
}

assets() {   # assets <run-dir> -> what was learned, and what used it
  local RUN="$1" arm have tools
  echo
  echo "=== learned assets ==="
  for arm in "$RUN"/*/; do
    arm="${arm%/}"
    [ -d "$arm/tasks" ] || continue
    echo "  --- ${arm##*/}"
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
      # Every skill with how many tasks pulled it back out. A skill written and
      # never retrieved is the thing this benchmark exists to detect, so the
      # count is the point, not decoration: "learned 3" has been true of runs
      # where all three were dead weight.
      python3 - "$arm" "$BUNDLED" <<'PY' 2>/dev/null
import json, pathlib, sys, collections

arm, bundled_dir = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
bundled = {p.name for p in bundled_dir.iterdir()} if bundled_dir.is_dir() else set()

retrieved, reused, cross = (collections.Counter() for _ in range(3))
results = arm / "results.jsonl"
if results.is_file():
    for line in results.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        for name in row.get("skills_retrieved") or []:
            retrieved[name] += 1
        for name in row.get("skills_reused") or []:
            reused[name] += 1
        for name in row.get("skills_reused_cross_repo") or []:
            cross[name] += 1

# results.jsonl only gains a row when a task FINISHES, so on a live run every
# skill reads "never retrieved" until the first task lands — which is the same
# false alarm as reporting an unstarted arm. The per-task retrieval log is
# written as it happens, so count in-flight tasks from there.
for log in (arm / "tasks").glob("*/retrievals.jsonl"):
    here = set()
    for line in log.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        here.update(record.get("skills") or [])
    for name in here:
        if not retrieved[name]:      # a finished task already counted it
            retrieved[name] += 1

store = arm / "store/.phronix/skills"
present = sorted(p.name for p in store.iterdir() if p.is_dir()) if store.is_dir() else []
# Learned first — they are what the run produced — then any seeded skill that
# actually got used. A seeded skill nobody touched is noise here.
learned = [n for n in present if n not in bundled]
seeded_used = [n for n in present if n in bundled and retrieved[n]]
for name in learned + seeded_used:
    kind = "+ skill" if name not in bundled else "  seeded"
    n = retrieved[name]
    if not n:
        note = "never retrieved"
    else:
        note = f"retrieved by {n} task(s)"
        if reused[name]:
            note += f", reused {reused[name]}"
        if cross[name]:
            note += f" ({cross[name]} cross-repo)"
    print(f"    {kind} {name:<44} {note}")
PY
      for tool in "$arm/store/.phronix/capabilities"/*.py; do
        [ -f "$tool" ] || continue
        base=$(basename "$tool" .py)
        case "$base" in probe_*) kind="method" ;; *) kind="solution" ;; esac
        echo "    + tool  $base ($kind)"
      done
    fi
  done
  python3 - "$RUN" <<'PY' 2>/dev/null
import json, pathlib, sys, collections
root = pathlib.Path(sys.argv[1])
# ---- were the learned skills and tools ever used? ------------------------
# Counted from the transcripts rather than retrievals.jsonl, because the
# retrieval log only fills in when the MCP server is reached at all — and the
# case worth catching is exactly the one where it never was.
BUNDLED = pathlib.Path(
    "/usr/WS2/haridev/phronix/src/phronix/.agents/skills")
bundled = {p.name for p in BUNDLED.iterdir()} if BUNDLED.is_dir() else set()

calls = collections.Counter()      # phronix tool -> times called
named = collections.Counter()      # skill/tool asked for by name -> times
per_arm = collections.Counter()    # arm -> phronix calls
# Arms run one after another, so an arm with no transcripts has not started
# yet. Reporting "nothing used the store" for it would be a false alarm — the
# claim is only meaningful about an arm that actually ran.
started, waiting = [], []
for arm in sorted(p for p in root.iterdir() if (p / "tasks").is_dir()):
    seen_any = False
    for tr in (arm / "tasks").glob("*/attempt-*/*.jsonl"):
        seen_any = True
        for line in tr.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            for block in ((event.get("message") or {}).get("content") or []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name") or ""
                if not name.startswith("mcp__phronix__"):
                    continue
                short = name[len("mcp__phronix__"):]
                calls[short] += 1
                per_arm[arm.name] += 1
                args = block.get("input") or {}
                for key in ("name", "skill", "query", "capability"):
                    value = args.get(key)
                    if isinstance(value, str) and value:
                        named[value] += 1
                        break
    (started if seen_any else waiting).append(arm.name)

print()
print("  --- what actually called the store")
for arm in waiting:
    print(f"  {arm}: not started yet — arms run in sequence")
# Only a phronix arm is expected to reach the store; a bare arm has no MCP
# server by design, so its zero is the control, not a fault.
expected = [a for a in started if "phronix" in a]
if not calls and expected:
    # The failure mode that hid for hours: server connected, nothing used it.
    print(f"  {', '.join(expected)} ran but called no phronix tool — the "
          f"store was written and never read")
elif not calls:
    if started:
        print(f"  {', '.join(started)}: bare arm, no store by design")
else:
    total = sum(calls.values())
    print(f"  {total} phronix tool call(s) across "
          f"{', '.join(f'{a} {n}' for a, n in per_arm.most_common())}")
    for tool, n in calls.most_common(12):
        print(f"    {n:>5}  {tool}")
    if named:
        print("  asked for by name (* = learned this run, not seeded):")
        for what, n in named.most_common(12):
            mark = " " if what in bundled else "*"
            print(f"    {n:>5} {mark} {what[:60]}")
PY
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

  # How fast the whole run is going, and whether anything learned is being
  # read back. Both are properties of the run rather than of one arm, so they
  # belong here — above the per-arm detail, not buried under it.
  overall "$RUN"

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


def _key():
    """The credential this endpoint wants, from the deployment that owns it.

    NOT `OPENAI_API_KEY`: a self-hosted cluster ships its own key in its own
    config, and the ambient variable belongs to a different service. Reporting
    "needs OPENAI_API_KEY" for a gateway the user deployed themselves sends them
    looking for a credential that was never involved.
    """
    for path in ("/usr/workspace/haridev/phronix/tuolumne-llm/cluster.json",):
        try:
            with open(path) as handle:
                key = (json.load(handle).get("gateway") or {}).get("key")
            if key:
                return str(key)
        except (OSError, ValueError):
            continue
    return os.environ.get("OPENAI_API_KEY", "")


def fetch(path, timeout=10):
    request = urllib.request.Request(f"{root}{path}")
    key = _key()
    if key:
        request.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _fleet():
    """Every backend behind the gateway, from the cluster's own config.

    The gateway does not publish llama.cpp's counters — it 404s on /metrics —
    but the backends do, and they answer unauthenticated. Reading them directly
    is the only way to see whether the FLEET is being used, as opposed to
    whether one endpoint is reachable. That distinction is the whole question
    when 32 GPUs are serving: a run can be healthy and still leave 24 of them
    idle.
    """
    try:
        with open("/usr/workspace/haridev/phronix/tuolumne-llm/cluster.json") as h:
            cfg = json.load(h)
    except (OSError, ValueError):
        return []
    gateway = cfg.get("gateway") or {}
    # Only when this run is actually pointed at that cluster.
    if f"{gateway.get('host')}:{gateway.get('port')}" not in base:
        return []
    return [(s.get("host"), s.get("port")) for s in cfg.get("servers") or []
            if s.get("host") and s.get("port")]


fleet = _fleet()
if fleet:
    import concurrent.futures

    def one(hp):
        host, port = hp
        try:
            with urllib.request.urlopen(
                    f"http://{host}:{port}/metrics", timeout=6) as response:
                text = response.read().decode("utf-8", "replace")
        except Exception:
            return None
        got = {}
        for line in text.splitlines():
            if line.startswith("llamacpp:"):
                name, _, value = line.partition(" ")
                try:
                    got[name] = float(value)
                except ValueError:
                    pass
        return got

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        seen = [g for g in pool.map(one, fleet) if g is not None]

    if seen:
        busy = sum(1 for g in seen if g.get("llamacpp:requests_processing", 0) > 0)
        inflight = sum(g.get("llamacpp:requests_processing", 0) for g in seen)
        deferred = sum(g.get("llamacpp:requests_deferred", 0) for g in seen)
        generated = sum(g.get("llamacpp:tokens_predicted_total", 0) for g in seen)
        rate = sum(g.get("llamacpp:predicted_tokens_seconds", 0) for g in seen)
        idle = len(seen) - busy
        # The headline: how much of the fleet the run is actually using. A
        # number nobody can act on is worse than none, and "24 idle" is the
        # most actionable thing this display can say.
        warn = ("  ** most of the fleet is idle — the run does not have enough "
                "concurrent agents to fill it" if idle > len(seen) / 2 else "")
        print(f"  fleet: {len(seen)}/{len(fleet)} backend(s) reachable, "
              f"{busy} busy / {idle} idle{warn}")
        print(f"         {inflight:.0f} request(s) in flight, {deferred:.0f} "
              f"queued   |   aggregate {rate:,.0f} tok/s")
        print(f"         {generated:,.0f} tokens generated across the fleet")
    raise SystemExit

try:
    raw = fetch("/metrics")
except (urllib.error.URLError, OSError) as exc:
    code = getattr(exc, "code", None)
    if code == 404:
        # Not every endpoint publishes metrics; that is not a fault.
        raise SystemExit
    why = ("rejected the credential from the cluster config" if code in (401, 403)
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

    # NOT 2>/dev/null. A syntax error in this block once removed every per-task
    # row while the summary above it still printed, so the display looked whole
    # and was missing the part anyone reads it for.
    python3 - "$arm/results.jsonl" <<'PY' || echo "  (per-task table failed to render — see the error above)"
import json, sys
from collections import OrderedDict


def human(seconds):
    """45s | 12m30s | 2h05m — the same shape the shell side writes."""
    s = int(seconds or 0)
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


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
            f"time={human(solve_t):>7}{money}")
    if research or learn:
        line += (f"   research tok={tokens(fresh_research, research)} "
                 f"time={human(research_t):>7}"
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
            # Whether the failure is moving. A task that fails differently each
            # try is converging; one that repeats itself is not, and pass/fail
            # alone cannot tell them apart. Outside the research block, because
            # it is true of every try whether or not that try researched.
            trend = a.get("failure_trend") or ""
            if trend == "moved":
                head += "  moved"
            elif trend == "same":
                head += f"  SAME x{a.get('same_failure_count') or 2}"
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
            f"time={human(totals['st']):>7}{money}")
    if totals["research"] or totals["learn"]:
        share = 100.0 * (totals["research"] + totals["learn"]) / grand if grand else 0
        line += (f"   research tok={tokens(totals['fresh_research'], totals['research'])} "
                 f"time={human(totals['rt']):>7}"
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

        # How long this task has been going, which is the number that says
        # whether it is worth waiting for. Silence alone cannot: 8s ago reads
        # the same on a task two minutes in and one at forty.
        #
        # From the FIRST event the task traced, not the directory's timestamps
        # — Lustre moves ctime on every append, so a task's own files report it
        # as newly created for as long as it keeps writing.
        started=$(grep "\] " "$task_dir/trace.log" 2>/dev/null | head -1 \
                  | awk '{print $1}')
        elapsed=""
        if [ -n "$started" ]; then
            began=$(date -d "$started" +%s 2>/dev/null || echo "")
            if [ -n "$began" ]; then
                # A run that crossed midnight parses as later today.
                [ "$began" -gt "$now" ] && began=$(( began - 86400 ))
                elapsed=$(human $(( now - began )))
            fi
        fi
        # kind and summary, from the line the task last wrote.
        rest=${last#*] }
        kind=${rest%% *}
        what=${rest#"$kind"}

        # A fanout stage names itself INSIDE the message, not in the stage.
        #
        # Serial stages trace as `research>tune:absolute-paths> looking around`,
        # where the stage is its own field. The members of a fanout run under
        # one parent stage and narrate through `on_call("[label] text")`, so the
        # line arrives as `research>   [aspect-record:pattern_type_effect] list`
        # — every one of five aspects showing an identical `research>` in the
        # stage column, with the only distinguishing part buried in the message
        # and then cut off by its width.
        #
        # Lift the bracketed label into the stage column where it belongs.
        trimmed=${what#"${what%%[![:space:]]*}"}
        case "$trimmed" in
          "["*"]"*)
            label=${trimmed%%]*}; label=${label#[}
            what=${trimmed#*]}
            kind="${kind}${label}>" ;;
        esac

        # A parallel member is a NUMBER, not its full name.
        #
        # `research>aspect:change_risk@gpt-oss-120b` spends most of the column
        # on two things the reader does not need: an aspect name already
        # visible in the message, and a backend alias that is an artefact of
        # load-spreading. What is actually wanted is "which of the five is
        # this", so the suffix becomes an index — `research>aspect#3`.
        #
        # Numbered by first appearance in this task's own trace, so the same
        # aspect keeps the same number across refreshes and between the
        # `aspect` and `aspect-record` lines that refer to it.
        case "$kind" in
          *:*)
            head_=${kind%%:*}          # research>aspect
            tail_=${kind#*:}           # change_risk@gpt-oss-120b>
            tail_=${tail_%>}
            base=${head_##*>}          # aspect
            # `]` excluded too: a fanout member is traced as
            # `[aspect:change_risk@gpt-oss-120b]`, so a class of just `[^ >]`
            # captured the closing bracket and never matched the lifted label.
            num=$(grep -oh "${base}:[^] >]*" "$task_dir/trace.log" 2>/dev/null \
                  | sed "s/^${base}://" | awk '!seen[$0]++' \
                  | grep -nxF -- "$tail_" 2>/dev/null | head -1 | cut -d: -f1)
            kind="${head_}#${num:-?}>"
            ;;
        esac

        # Eighty characters, because that is what the describer writes. Cut at
        # 46 the line read "searching the source for def load_dot" — the width
        # threw away the half of the sentence that says what is being looked
        # for, which is the only part that distinguishes one line from the next.
        what=$(echo "$what" | cut -c1-46)
        # The stage column has to hold `research>aspect-record:pattern-type>`,
        # so it is wide enough for that and the message keeps its 46.
        kind=$(echo "$kind" | cut -c1-40)
        # "Quiet", not "idle", and on a much longer fuse.
        #
        # This measures silence in the TRACE, which ticks only when an event
        # arrives — a tool call returning, a text block completing. A single
        # model turn produces nothing until it finishes, and at ~150 tok/s that
        # is minutes. Measured: seven tasks marked idle while the fleet was
        # serving exactly seven requests, so every one of them was mid-turn.
        #
        # The fleet line above is the real check: if tasks-in-flight matches
        # requests-in-flight, nothing is stuck however quiet it looks. A stall
        # shows up as tasks WITHOUT requests, which is how the stderr deadlock
        # was found.
        mark=""
        [ "$idle" -gt "${PHRONIX_QUIET_SECONDS:-900}" ] && mark="  ** quiet"
        printf "    %-26s %-7s%-26s %-46s %7s (%s ago)%s\n" \
               "${name#*-}" "$try_mark" "$kind" "$what" "$elapsed" \
               "$(human "$idle")" "$mark"
      done
      echo "    follow one:  tail -f $arm/tasks/<task>/trace.log"
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

  assets "$RUN"
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
