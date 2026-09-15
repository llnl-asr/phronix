#!/usr/bin/env python3
"""Eval 5, per STEP -- what each pipeline step cost and how hard it was.

``eval5_extract.py`` answers "what did this session cost in total". This
answers "where did the effort go", which is the part of eval 5 that shows the
approach working: a step that succeeded on the first call and a step that
needed twelve retries both end in success, and only the second one is
evidence of anything.

Columns
-------
`calls_ok` / `calls_failed`
    Tool calls inside the step, split by whether the result came back flagged
    is_error. Failures are attributed to the step that made the CALL, not the
    step that happened to be open when the result arrived -- an annotation
    subagent's failure belongs to annotation.
`repeats`
    Calls beyond the first with identical name AND arguments. Same call again
    is the agent circling; same tool with new arguments is progress.
`repairs`
    Edits to MCP tool source under ``mcp_tools/``. This is what "learning"
    looks like in a pipeline run: the session did not write skills, it fixed
    the tools it was failing on, and those fixes outlive the session. Without
    this column the capability axis reads zero and the run looks like it
    learned nothing.
`seconds`
    Wall time between the step's profile_step_begin and its profile_step_end.

A step that begins and never ends is still emitted, with ``ended=0``: that IS
the failure mode, since a collapsing step does not report its own collapse.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter
from pathlib import Path

FIELDS = ["order", "step", "calls_ok", "calls_failed", "repeats",
          "repairs", "seconds", "ended",
          "skills_ok", "skills_failed", "tools_ok", "tools_failed",
          "other_ok", "other_failed",
          "tokens_in", "tokens_out", "turns", "gen_chars"]

#: The four phases the paper reports, and which steps roll into each. The
#: pipeline's own step names are an implementation detail; the phases are what
#: a reader can compare against a bare run, which has no steps at all.
#:
#: annotate takes validation and the init/fini fix with it: both only exist
#: because annotation happened, and splitting them would credit annotation
#: with less work than it caused.
PHASES = ["setup", "annotate", "build", "smoke"]
PHASE_OF_STEP = {
    "(setup)": "setup",
    "STEP 1: session setup + detect": "setup",
    "STEP 2: build annotated baseline (no macros) + validate structure": "build",
    "STEP 3: whole-project annotation": "annotate",
    "STEP: dftracer-annotate-c (IOR)": "annotate",
    "STEP: dftracer-validate-c": "annotate",
    "STEP: fix-init-fini-ordering": "annotate",
    "STEP 4-5: build annotated + smoke test": "build",
    # A bare run's steps ARE the phases: they come from its todo list, which
    # names the phase directly (see TODO_PHASE).
    "setup": "setup",
    "annotate": "annotate",
    "build": "build",
    "smoke": "smoke",
}

#: The smoke test lives inside a step that also builds, so it cannot be
#: separated by step name. These tool names are the smoke phase wherever they
#: are called from.
SMOKE_TOOLS = ("session_run_smoke_test", "session_identify_smoke_test_files")

#: A bare run has no profile_step markers -- those come from the pipeline's
#: MCP server, which is exactly what "bare" means it does not have. What it
#: does keep is a todo list, and the todo it marks in_progress is the same
#: claim about what it is working on. Tested in order, so "Build annotated
#: IOR" is build rather than annotate.
TODO_PHASE = (
    ("smoke", ("smoke", "smoke test")),
    ("build", ("build", "compile", "configure")),
    ("annotate", ("annotat",)),
    ("setup", ("clone", "venv", "install", "environment", "setup")),
)


def phase_of_todo(text: str) -> str:
    """Phase a bare run's in-progress todo belongs to."""
    low = text.lower()
    for phase, words in TODO_PHASE:
        if any(w in low for w in words):
            return phase
    return "setup"

PHASE_FIELDS = ["arm", "phase", "skills_ok", "skills_failed",
                "tools_ok", "tools_failed", "other_ok", "other_failed",
                "calls", "tokens_in", "tokens_out",
                "tokens_in_per_call", "tokens_out_per_call",
                "repairs", "seconds"]


def _is_skill(name: str) -> bool:
    """A capability that is KNOWLEDGE: a skill being loaded or invoked."""
    return name in ("Skill",) or name.endswith(("skill_load", "skill_search"))


def records(path: Path):
    for line in path.open(errors="replace"):
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _stamp(event: dict) -> float:
    """Event time as a POSIX float, or 0.0 when the event carries none."""
    raw = event.get("timestamp") or ""
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def scan(path: Path) -> list[dict]:
    steps: list[dict] = []
    by_name: dict[str, dict] = {}
    open_stack: list[str] = []
    call_step: dict[str, str] = {}      # tool_use id -> step that called it
    call_kind: dict[str, str] = {}      # tool_use id -> "skills" | "tools"
    call_phase: dict[str, str] = {}     # tool_use id -> phase override
    smoke_extra: Counter = Counter()    # capability counts owed to smoke
    smoke_work: Counter = Counter()     # turns/gen_chars owed to smoke
    seen: Counter = Counter()

    current_todo = ["(setup)"]          # bare run's phase, from its todo list

    def current() -> str:
        return open_stack[-1] if open_stack else current_todo[0]

    def ensure(name: str) -> dict:
        if name not in by_name:
            row = {k: 0 for k in FIELDS}
            row.update(step=name, order=len(steps) + 1)
            by_name[name] = row
            steps.append(row)
        return by_name[name]

    ensure("(setup)")

    for event in records(path):
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        # Per-message `usage` in a stream-json log CANNOT be summed: output is
        # a streaming partial (never above 34 tokens a message) and cache
        # counters repeat the same prefix every turn, over-counting 4-5x.
        # Only the run's final `result` event carries true totals. So measure
        # per-phase ACTIVITY here and apportion those totals in rollup().
        usage = message.get("usage") or {}
        if usage:
            ensure(current())["turns"] += 1

        content = message.get("content")
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            if block.get("type") in ("text", "thinking"):
                ensure(current())["gen_chars"] += len(
                    block.get("text") or block.get("thinking") or "")

            if block.get("type") == "tool_use":
                ensure(current())["gen_chars"] += len(
                    json.dumps(block.get("input") or {}))
                name = str(block.get("name", "?"))
                step = ensure(current())
                call_step[str(block.get("id"))] = step["step"]
                # Remember what KIND of capability this was, so the result can
                # be filed as a skill or an MCP tool when it comes back.
                # Every call is exactly one of three kinds. "other" is not a
                # leftover bin: it is how a bare run does all of its work
                # (Bash, Read, Edit), and without it bare's bars are empty and
                # the comparison looks like bare did nothing.
                call_kind[str(block.get("id"))] = (
                    "skills" if _is_skill(name)
                    else "tools" if name.startswith("mcp__")
                    else "other"
                )
                if any(name.endswith(t) for t in SMOKE_TOOLS):
                    call_phase[str(block.get("id"))] = "smoke"
                    # The TURN that issued the smoke call belongs to smoke
                    # too. Without this the phase owns calls but no turns, so
                    # the token apportionment gives it zero and the figure
                    # draws a gap where there was real work.
                    smoke_work["turns"] += 1
                    smoke_work["gen_chars"] += len(
                        json.dumps(block.get("input") or {}))

                key = (name, json.dumps(block.get("input"), sort_keys=True)[:400])
                seen[key] += 1
                if seen[key] > 1:
                    step["repeats"] += 1

                # A repair is an edit to the tool source itself. That is the
                # durable artefact of a pipeline run, and the only thing here
                # that survives the session.
                if name in ("Edit", "Write", "MultiEdit"):
                    target = str((block.get("input") or {}).get("file_path", ""))
                    if "/mcp_tools/" in target:
                        step["repairs"] += 1

                # A bare run announces its phase by marking a todo in_progress.
                # Only honoured while no profile_step is open, so a pipeline
                # run's own markers always win.
                if name == "TodoWrite" and not open_stack:
                    for todo in (block.get("input") or {}).get("todos", []):
                        if todo.get("status") == "in_progress":
                            todo_phase = phase_of_todo(str(todo.get("content", "")))
                            ensure(todo_phase)["ended"] = 1
                            current_todo[0] = todo_phase
                            break

                if name.endswith("profile_step_begin"):
                    label = str((block.get("input") or {}).get("step", "?"))
                    row = ensure(label)
                    row["_t0"] = _stamp(event)
                    open_stack.append(label)
                elif name.endswith("profile_step_end") and open_stack:
                    label = open_stack.pop()
                    row = by_name.get(label)
                    if row is not None:
                        row["ended"] = 1
                        if row.get("_t0"):
                            row["seconds"] = round(_stamp(event) - row["_t0"])

            elif block.get("type") == "tool_result":
                # Attribute to the step that made the call, not whatever is
                # open now -- results can land after the step moved on.
                cid = str(block.get("tool_use_id"))
                owner = call_step.get(cid, current())
                row = ensure(owner)
                bad = bool(block.get("is_error"))
                row["calls_failed" if bad else "calls_ok"] += 1
                kind = call_kind.get(cid, "other")
                if kind:
                    row[f"{kind}_failed" if bad else f"{kind}_ok"] += 1
                    if cid in call_phase:
                        smoke_extra[
                            f"{kind}_failed" if bad else f"{kind}_ok"] += 1

    for row in steps:
        row.pop("_t0", None)
    return steps, smoke_extra, smoke_work


def empty_arm(arm: str) -> list[dict]:
    """All-zero rows for an arm that has not been run yet.

    The bare baseline is a placeholder until that run exists. Zeros are
    honest here only because the figure's legend says the arm is not yet
    measured -- a reader must not mistake "not run" for "did nothing".
    """
    return [{k: 0 for k in PHASE_FIELDS} | {"phase": p, "arm": arm}
            for p in PHASES]


def run_totals(path: Path) -> dict:
    """True token totals, from the run's final `result` event.

    The only trustworthy token numbers in a stream-json log. Input counts
    cache reads and writes: they are context the model was sent, billed
    cheaper but not free.
    """
    for event in records(path):
        if event.get("type") == "result" and isinstance(event.get("usage"), dict):
            u = event["usage"]
            return {
                "in": ((u.get("input_tokens", 0) or 0)
                       + (u.get("cache_read_input_tokens", 0) or 0)
                       + (u.get("cache_creation_input_tokens", 0) or 0)),
                "out": u.get("output_tokens", 0) or 0,
                "cost": event.get("total_cost_usd", 0) or 0,
            }
    raise SystemExit(
        "eval5_steps: no result event with usage. Token totals cannot be "
        "recovered from per-message usage -- it is a streaming partial.")


def rollup(steps: list[dict], smoke_extra: Counter, smoke_work: Counter,
           totals: dict,
           arm: str = "phronix") -> list[dict]:
    """Collapse steps into the four reported phases."""
    # turns/gen_chars are working columns for the apportionment below and are
    # dropped before the CSV is written. Seeded here because a phase can exist
    # with no step of its own -- phronix's smoke is carved out by tool name.
    phases = {p: {k: 0 for k in PHASE_FIELDS} | {"phase": p, "arm": arm,
                                                 "turns": 0, "gen_chars": 0}
              for p in PHASES}

    for row in steps:
        try:
            target = phases[PHASE_OF_STEP[row["step"]]]
        except KeyError:
            raise SystemExit(
                f"eval5_steps: step {row['step']!r} is in no phase.\n"
                f"Add it to PHASE_OF_STEP -- a step silently dropped from the "
                f"rollup makes the figure understate the run."
            ) from None
        for field in ("skills_ok", "skills_failed", "tools_ok", "tools_failed",
                      "other_ok", "other_failed", "repairs", "seconds"):
            target[field] += row[field]
        # Work done in the phase: every tool call, of any kind. Bash counts --
        # it is how a bare run does its work, and a measure that only counted
        # MCP calls would score bare at zero work and make tokens-per-action
        # undefined for it.
        target["calls"] += row["calls_ok"] + row["calls_failed"]
        target["turns"] = target.get("turns", 0) + row["turns"]
        target["gen_chars"] = target.get("gen_chars", 0) + row["gen_chars"]

    # The smoke test is charged to smoke, not to the build step that hosts it.
    # Its calls move with it, or smoke shows capabilities but no work and the
    # per-call normalisation divides by zero.
    moved = 0
    for field, count in smoke_extra.items():
        phases["build"][field] -= count
        phases["smoke"][field] += count
        moved += count
    phases["build"]["calls"] -= moved
    phases["smoke"]["calls"] += moved
    # ... and the turns that issued them, so the token apportionment below has
    # something to divide into smoke instead of leaving it at zero.
    for field, count in smoke_work.items():
        phases["build"][field] -= count
        phases["smoke"][field] += count

    # Apportion the run's TRUE totals across phases. Input follows assistant
    # turns, because every turn re-sends the whole context and that is what
    # input tokens are; output follows generated characters, because that is
    # what the model actually produced. Neither share can be read off the
    # per-message usage, which is a streaming partial (see scan()).
    rows = [phases[p] for p in PHASES]
    for field, total, weight in (("tokens_in", totals.get("in", 0), "turns"),
                                 ("tokens_out", totals.get("out", 0), "gen_chars")):
        pool = sum(r[weight] for r in rows) or 1
        for r in rows:
            r[field] = round(total * r[weight] / pool)

    # Normalised: what one action cost. This is the fair comparison -- an arm
    # that annotates 418 regions and one that annotates 9 are not doing the
    # same amount of work, so their raw totals are not comparable.
    for r in rows:
        calls = r["calls"] or 1
        r["tokens_in_per_call"] = round(r["tokens_in"] / calls)
        r["tokens_out_per_call"] = round(r["tokens_out"] / calls)
        r.pop("turns", None)
        r.pop("gen_chars", None)

    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stream", help="headless run stream-json (.jsonl)")
    ap.add_argument("--out", default="eval5_steps.csv")
    ap.add_argument("--phases-out", default="eval5_phases.csv",
                    help="four-phase rollup, the input eval5_plot.py reads")
    ap.add_argument("--arm", default="phronix",
                    help="name this run's arm in the phase rollup")
    ap.add_argument("--empty-arm", default="bare",
                    help="also emit all-zero rows for this arm, as a "
                         "placeholder until it is actually run "
                         "(empty string to omit)")
    args = ap.parse_args()

    all_steps, smoke_extra, smoke_work = scan(Path(args.stream))
    steps = [s for s in all_steps if s["calls_ok"] or s["calls_failed"]]

    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(steps)

    phases = rollup(steps, smoke_extra, smoke_work,
                    run_totals(Path(args.stream)),
                    arm=args.arm)
    if args.empty_arm:
        phases += empty_arm(args.empty_arm)
    with open(args.phases_out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PHASE_FIELDS)
        w.writeheader()
        w.writerows(phases)

    print(f"{args.out}: {len(steps)} step(s)")
    for s in steps:
        flag = "" if s["ended"] else "  UNFINISHED"
        print(f"  {s['order']:2d}. {s['step'][:44]:<44} "
              f"ok={s['calls_ok']:4d} fail={s['calls_failed']:3d} "
              f"rep={s['repeats']:3d} fix={s['repairs']:2d} "
              f"{s['seconds']:5d}s{flag}")

    print(f"\n{args.phases_out}: {len(phases)} phase(s)")
    for p in phases:
        print(f"  {p['phase']:<9} skills={p['skills_ok']:3d}/{p['skills_failed']:<3d} "
              f"tools={p['tools_ok']:4d}/{p['tools_failed']:<3d} "
              f"fix={p['repairs']:2d}  "
              f"tok in={p['tokens_in']:,} out={p['tokens_out']:,}")


if __name__ == "__main__":
    main()
