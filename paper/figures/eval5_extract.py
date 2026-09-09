#!/usr/bin/env python3
"""Eval 5 -- one agentic pipeline session, measured.

Reads a Claude Code session transcript and reports what the session cost and
what it produced. Works on both shapes of transcript:

* interactive sessions, under ``~/.claude/projects/<slug>/<uuid>.jsonl``
* headless runs (``--print --output-format stream-json``) written to a file

They carry the same records; the interactive one adds the human turns, which
is the point of measuring it at all.

What the columns mean
---------------------
`human_turns`    -- messages the person actually typed. Detected by
                    ``origin.kind == "human"``: every other `user` record is a
                    tool result being fed back, and counting those would report
                    hundreds of "interactions" for an unattended run.
`steps_*`        -- pipeline steps, from the profile_step_begin/end markers.
                    A step that began and never ended is counted as failed;
                    that IS the failure mode -- a step does not report its own
                    collapse.
`calls_failed`   -- tool results flagged is_error. This is the honest retry
                    signal: the pipeline keeps no retry counter, so a step
                    that called one tool twenty times shows up here and in
                    `repeats`.
`repeats`        -- calls beyond the first to the same tool with the same
                    arguments. A tool called twice with different arguments is
                    progress; the same call again is the agent circling.
`skills_written` -- skill_write / capability_new calls that succeeded.
`tools_written`  -- capability modules created (MCP tools the session built).
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import Counter
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"

# Tool names that mean "the session wrote durable knowledge". Both frameworks
# expose their own spelling, so match on the suffix rather than the server.
SKILL_WRITERS = ("skill_write", "skill_write_lesson", "skill_define")
TOOL_WRITERS = ("capability_new",)

FIELDS = ["session", "arm", "model", "human_turns", "assistant_turns",
          "calls_total", "calls_failed", "repeats",
          "steps_begun", "steps_ended", "steps_failed",
          "skills_written", "tools_written",
          "tokens_in", "tokens_out", "tokens_cache", "tokens_total", "cost_usd"]


def records(path: Path):
    for line in path.open(errors="replace"):
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def scan(path: Path, arm: str) -> dict:
    row = {k: 0 for k in FIELDS if k not in ("session", "arm", "model")}
    row.update(session=path.stem[:8], arm=arm, model="")
    seen_calls: Counter = Counter()
    # A failure has to be charged to the call that caused it, and the result
    # arrives in a later record, so the id is the only link.
    call_of: dict[str, str] = {}
    steps_open: list[str] = []

    for event in records(path):
        kind = event.get("type")

        if kind == "user":
            if (event.get("origin") or {}).get("kind") == "human":
                row["human_turns"] += 1
            content = event.get("message", {}).get("content")
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result" and block.get("is_error"):
                    row["calls_failed"] += 1

        elif kind == "assistant":
            row["assistant_turns"] += 1
            message = event.get("message", {})
            if message.get("model") and not row["model"]:
                row["model"] = message["model"]
            usage = message.get("usage") or {}
            row["tokens_in"] += usage.get("input_tokens", 0) or 0
            row["tokens_out"] += usage.get("output_tokens", 0) or 0
            row["tokens_cache"] += ((usage.get("cache_read_input_tokens", 0) or 0)
                                    + (usage.get("cache_creation_input_tokens", 0) or 0))
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue
                name = str(block.get("name", "?"))
                row["calls_total"] += 1
                call_of[str(block.get("id"))] = name
                # Identical call, identical arguments: the second one is the
                # agent going round again, not doing more work.
                key = (name, json.dumps(block.get("input"), sort_keys=True)[:400])
                seen_calls[key] += 1
                if seen_calls[key] > 1:
                    row["repeats"] += 1

                if name.endswith("profile_step_begin"):
                    row["steps_begun"] += 1
                    steps_open.append(str((block.get("input") or {}).get("step", "?")))
                elif name.endswith("profile_step_end"):
                    row["steps_ended"] += 1
                    if steps_open:
                        steps_open.pop()
                elif any(name.endswith(w) for w in SKILL_WRITERS):
                    row["skills_written"] += 1
                elif any(name.endswith(w) for w in TOOL_WRITERS):
                    row["tools_written"] += 1

        elif kind == "result":
            row["cost_usd"] = round(event.get("total_cost_usd", 0) or 0, 4)

    # A step still open at the end never finished. Nothing else records that.
    row["steps_failed"] = len(steps_open)
    row["tokens_total"] = row["tokens_in"] + row["tokens_out"] + row["tokens_cache"]
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phronix", nargs="*", default=[],
                    help="transcripts of phronix-enhanced sessions")
    ap.add_argument("--bare", nargs="*", default=[],
                    help="transcripts of bare sessions (no phronix/dftracer MCP)")
    ap.add_argument("--project", default="-usr-WS2-haridev-dftracer-agents",
                    help="project slug under ~/.claude/projects, for --latest")
    ap.add_argument("--latest", type=int, default=0,
                    help="also take the N newest transcripts of that project as phronix")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "eval5_session.csv")
    args = ap.parse_args()

    jobs = [(Path(p), "phronix") for p in args.phronix]
    jobs += [(Path(p), "bare") for p in args.bare]
    if args.latest:
        found = sorted(glob.glob(str(PROJECTS / args.project / "*.jsonl")),
                       key=os.path.getmtime, reverse=True)[:args.latest]
        jobs += [(Path(p), "phronix") for p in found]

    rows = [scan(p, arm) for p, arm in jobs if p.is_file()]
    if not rows:
        raise SystemExit("no transcripts found")

    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} session(s)")
    for r in rows:
        print(f"  {r['arm']:8s} {r['session']}  human={r['human_turns']:3d} "
              f"calls={r['calls_total']:4d} failed={r['calls_failed']:3d} "
              f"repeats={r['repeats']:3d} steps={r['steps_begun']}/{r['steps_ended']} "
              f"skills={r['skills_written']:2d} tools={r['tools_written']:2d} "
              f"tok={r['tokens_total']:,}")


if __name__ == "__main__":
    main()
