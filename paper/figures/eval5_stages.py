#!/usr/bin/env python3
"""Eval 5a data: per stage, per kind of tool, for both arms.

Stage attribution here classifies the ACTION a call performs -- the MCP tool
invoked, or for a shell call the command actually run. It never reads the
agent's prose.

That distinction is the whole design. An earlier version matched patterns
across tool inputs AND results, which meant the words ".pfw" or "dft_fn"
appearing in the brief or in a loaded skill advanced the phase before any such
work happened: phronix landed 92 of 101 calls in "trace" on its first turn
while bare never left "setup". A command string is a thing being executed; a
sentence is not.

Calls belonging to no stage are reported under `overhead` rather than being
swept into a neighbour. That bucket is not a measurement gap -- it is real
work that serves the run rather than the job: harness coordination
(ToolSearch, Agent, SendMessage), planning (TodoWrite), and waiting on or
grepping logs. For phronix it is where the stalled background-agent detour
shows up.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

STAGES = ["setup", "annotate", "smoke", "trace", "tooling", "overhead"]
KINDS = ["mcp", "skills", "bash"]

#: MCP tool name -> stage. Matched on the bare tool name (after the server
#: prefix), longest first so `session_run_with_dftracer` beats `session_run`.
MCP_STAGE = [
    ("annotate", ("session_write_file", "python_annotate", "python_extract",
                  "python_lint",
                  "python_dedup", "clang_annotate", "clang_lint",
                  "clang_extract", "clang_syntax", "validate_annotations",
                  "session_copy_annotated", "annotate_add_app_metadata",
                  "session_annotation_report", "clang_write_annotated",
                  "clang_insert_line")),
    ("trace",    ("session_run_with_dftracer", "session_analyze_traces",
                  "event_count", "dftracer_info", "session_split_traces",
                  "session_validate_traces", "trace")),
    ("smoke",    ("session_run_smoke_test", "session_identify_smoke_test",
                  "session_build_annotated", "session_build_install")),
    ("setup",    ("session_create", "session_detect", "system_detect",
                  "session_install", "session_configure", "session_stage",
                  "session_reorganize", "session_validate_structure",
                  "session_status", "session_read_file", "profile_",
                  "skill_", "graph_", "memory_", "session_ml_")),
]

#: Shell command -> stage, by what the command DOES.
BASH_STAGE = [
    # Building or repairing an MCP tool is the framework improving itself. It
    # is work the run did, not friction it suffered, so it gets its own stage
    # rather than being written off as overhead.
    ("tooling",  r"mcp_tools/|dftracer_agents/src|def [a-z_]+\(.*\).*mcp|"
                 r"@mcp\.tool|dftracer-mcp-server"),
    ("trace",    r"\.pfw|DFTRACER_LOG_FILE|dftracer_info|gzip -dc|zcat .*pfw"),
    ("smoke",    r"individuals\.py\s+\S+\s+\d|main\.py .*--data_dir|"
                 r"\./src/ior|flux run"),
    ("annotate", r"python_annotate|compileall|py_compile|"
                 r"grep -n .*dft_fn|import dftracer"),
    ("setup",    r"git clone|pip install|python -m venv|module load|"
                 r"module avail|mkdir|which |ls |cat |cd |requirements|"
                 # proving GitLab reachability and reading the install log are
                 # both setup work, not overhead
                 r"ssh -T git@|dftracer_install\.log|git config"),
]


def records(path: Path):
    for line in path.open(errors="replace"):
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def classify(name: str, inp: dict) -> tuple[str, str]:
    """(kind, stage) for one call."""
    if name.startswith("mcp__"):
        bare = name.split("__")[-1]
        kind = "skills" if bare.startswith("skill_") else "mcp"
        for stage, keys in MCP_STAGE:
            if any(k in bare for k in keys):
                return kind, stage
        return kind, "overhead"
    if name in ("Skill",):
        return "skills", "setup"
    if name == "Bash":
        cmd = str((inp or {}).get("command", ""))
        for stage, pat in BASH_STAGE:
            if re.search(pat, cmd, re.I):
                return "bash", stage
        return "bash", "overhead"
    # Read/Edit/Write/Glob/Grep: editing the app is annotation work; the rest
    # is orientation, which belongs to whatever it was orienting for and so is
    # left unclassified rather than guessed.
    if name in ("Edit", "Write", "MultiEdit"):
        target = str((inp or {}).get("file_path", ""))
        return "bash", ("annotate" if re.search(r"/bin/|\.py$", target)
                        else "overhead")
    return "bash", "overhead"


def scan(path: Path, arm: str) -> list[dict]:
    cell = defaultdict(lambda: {"ok": 0, "failed": 0, "denied": 0})
    kinds_of = {}
    totals = {"in": 0, "out": 0, "cost": 0.0}
    turns = defaultdict(int)
    gen = defaultdict(int)
    order = []

    for event in records(path):
        if event.get("type") == "result":
            # MAX, not sum. A phronix run emits one result per agent context
            # and each reports the SESSION's cumulative cost, so adding them
            # would double-count. Token fields in those events describe only
            # the sub-agent that emitted them and are not usable -- which is
            # why cost, not tokens, is what this figure plots.
            totals["cost"] = max(totals["cost"],
                                 float(event.get("total_cost_usd", 0) or 0))
        if event.get("type") == "result" and isinstance(event.get("usage"), dict):
            u = event["usage"]
            totals["in"] = ((u.get("input_tokens", 0) or 0)
                            + (u.get("cache_read_input_tokens", 0) or 0)
                            + (u.get("cache_creation_input_tokens", 0) or 0))
            totals["out"] = u.get("output_tokens", 0) or 0
        msg = event.get("message")
        if not isinstance(msg, dict):
            continue
        has_usage = bool(msg.get("usage"))
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        msg_stages: list[str] = []
        gen_pending: list[int] = []
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                kind, stage = classify(str(b.get("name", "")), b.get("input"))
                kinds_of[str(b.get("id"))] = (kind, stage)
                order.append(stage)
                msg_stages.append(stage)
                gen[stage] += len(json.dumps(b.get("input") or {}))
            if b.get("type") in ("text", "thinking"):
                gen_pending.append(len(b.get("text") or b.get("thinking") or ""))

            elif b.get("type") == "tool_result":
                kind, stage = kinds_of.get(str(b.get("tool_use_id")),
                                           ("bash", "overhead"))
                c = b.get("content")
                text = c if isinstance(c, str) else json.dumps(c)
                # A tool can return "successfully" while its payload says the
                # job failed -- session_run_smoke_test reported
                # '"status": "error", "message": "Smoke test failed"' with
                # is_error unset. Counting only is_error scored that as a win.
                payload_error = ('"status": "error"' in text
                                 or '\\"status\\": \\"error\\"' in text)
                # A permission denial is the harness refusing, not the arm
                # getting it wrong. Scoring it as a failure blames the
                # framework for the sandbox.
                denied = "tool use was rejected" in text or (
                    "doesn't want to proceed" in text)
                if denied:
                    cell[(stage, kind)]["denied"] += 1
                elif b.get("is_error") or payload_error:
                    cell[(stage, kind)]["failed"] += 1
                else:
                    cell[(stage, kind)]["ok"] += 1

        # ONE assistant turn, charged to the stage that turn worked on. Counting
        # a turn per CALL instead made input-per-action constant by
        # construction (input was apportioned by call count and then divided
        # by call count), which is why the input line had to be dropped.
        if has_usage and msg_stages:
            turns[max(set(msg_stages), key=msg_stages.count)] += 1
        elif has_usage:
            turns["overhead"] += 1

    pool_t = sum(turns.values()) or 1

    pool_g = sum(gen.values()) or 1
    rows = []
    for stage in STAGES:
        t_in = round(totals["in"] * turns[stage] / pool_t)
        t_out = round(totals["out"] * gen[stage] / pool_g)
        # Cost follows assistant TURNS: one turn is one API call, and that is
        # what is billed. Then divided by the calls the stage made, so the
        # arms are compared per unit of work rather than per run.
        stage_cost = totals["cost"] * turns[stage] / pool_t
        calls = sum(cell[(stage, k)]["ok"] + cell[(stage, k)]["failed"]
                    + cell[(stage, k)]["denied"] for k in KINDS)
        for kind in KINDS:
            c = cell[(stage, kind)]
            rows.append({
                "arm": arm, "stage": stage, "kind": kind,
                "ok": c["ok"], "failed": c["failed"], "denied": c["denied"],
                "tokens_in": t_in if kind == KINDS[0] else 0,
                "tokens_out": t_out if kind == KINDS[0] else 0,
                "stage_calls": calls,
                "tokens_in_per_call": round(t_in / calls) if calls else 0,
                "tokens_out_per_call": round(t_out / calls) if calls else 0,
                "cost_usd": round(stage_cost, 4),
                "cost_per_call": round(stage_cost / calls, 4) if calls else 0,
            })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bare", required=True)
    ap.add_argument("--phronix", required=True)
    ap.add_argument("--out", default="eval5_stages.csv")
    args = ap.parse_args()

    rows = (scan(Path(args.bare), "bare")
            + scan(Path(args.phronix), "phronix"))
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out}")

    for arm in ("bare", "phronix"):
        sub = [r for r in rows if r["arm"] == arm]
        tot = sum(r["ok"] + r["failed"] + r["denied"] for r in sub)
        print(f"\n{arm}: {tot} calls")
        for stage in STAGES:
            st = [r for r in sub if r["stage"] == stage]
            n = sum(r["ok"] + r["failed"] + r["denied"] for r in st)
            if not n:
                continue
            by = "  ".join(
                f"{r['kind']}={r['ok']}ok/{r['failed']}fail/{r['denied']}denied"
                for r in st if r["ok"] or r["failed"] or r["denied"])
            print(f"   {stage:<13} {n:>4}  {by}")


if __name__ == "__main__":
    main()
