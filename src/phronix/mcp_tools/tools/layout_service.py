"""Layout: is a solution filed where the rest of the system will find it?

A solution that is correct and misfiled is a solution nothing reuses, and the
failure is silent — the writer succeeds, and the next run's lookup simply
returns nothing. Every such failure so far has been of that shape: answers
written loose where `--fresh` could not hide them, a slug nested inside itself,
a task's diagnosis under a name no reader asks for.

So the layout is checked rather than assumed, and the check is a tool the
research agent can call on its own work before it finishes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

#: `capabilities/skills/<TaskName>/SKILL.md` (+ helper notes the skill links to)
#: `capabilities/tools/<category>/<name>.py`
#: and the same two shapes under `research/`, where the slug is what was
#: SEARCHED FOR rather than the task at hand.
SOLUTION_DIR = "skills"
TOOL_DIR = "tools"
TREES = ("capabilities", "research")


def _issues_for(root: Path, tree: str) -> List[Dict[str, str]]:
    """Everything filed wrongly under one tree, with what to do about it."""
    base = root / tree
    out: List[Dict[str, str]] = []
    if not base.is_dir():
        return out

    for entry in sorted(base.iterdir()):
        name = entry.name
        if entry.is_file():
            # A loose file is the shape that defeats `--fresh`: the filter
            # keys on the directory, so anything at the top of the tree is
            # served to every from-scratch run for good.
            # A flat `<subject>.json` is the pre-restructure record layout.
            if tree == "research" and entry.suffix == ".json":
                out.append({
                    "path": f"{tree}/{name}",
                    "problem": "a record loose at the top of the tree",
                    "fix": f"move it to {tree}/{SOLUTION_DIR}/{entry.stem}/record.json "
                           f"— one directory per subject, record beside the "
                           f"skill it produced",
                })
                continue
            if entry.suffix == ".py":
                out.append({
                    "path": f"{tree}/{name}",
                    "problem": "a tool sitting loose at the top of the tree",
                    "fix": f"move it to {tree}/{TOOL_DIR}/<category>/{name} — "
                           f"the category is what the tool is ABOUT",
                })
            continue
        if name in (SOLUTION_DIR, TOOL_DIR, "sessions"):
            continue
        # `observations.jsonl` and its cursor are the always-on learner's
        # INPUT, not filed content.
        if tree == "research" and name in ("observations", "cursors"):
            continue
        out.append({
            "path": f"{tree}/{name}/",
            "problem": f"not one of {tree}/{SOLUTION_DIR} or {tree}/{TOOL_DIR}",
            "fix": f"a solution goes to {tree}/{SOLUTION_DIR}/<name>/SKILL.md; "
                   f"a deterministic tool goes to {tree}/{TOOL_DIR}/<category>/",
        })

    for solution in sorted((base / SOLUTION_DIR).glob("*")):
        if not solution.is_dir():
            continue
        # Under `research/` the RECORD is a legitimate artifact on its own:
        # a subject can be investigated and written down before it has
        # produced a skill. Under `capabilities/` it cannot — a task's
        # solution is the skill.
        has_record = (solution / "record.json").is_file()
        if not (solution / "SKILL.md").is_file() and not (
                tree == "research" and has_record):
            out.append({
                "path": f"{tree}/{SOLUTION_DIR}/{solution.name}/",
                "problem": ("nothing in it — no SKILL.md and no record"
                            if tree == "research" else
                            "no SKILL.md, so no reader will find it"),
                "fix": "write the solution with skill_write; helper notes sit "
                       "beside it and are LINKED from SKILL.md",
            })
        try:
            skill_text = (solution / "SKILL.md").read_text(errors="replace")
        except OSError:
            skill_text = ""
        # The slug nested inside itself, which is what the old layout did.
        if (solution / solution.name).is_dir():
            out.append({
                "path": f"{tree}/{SOLUTION_DIR}/{solution.name}/{solution.name}/",
                "problem": "the name is nested inside itself",
                "fix": f"move the files up one level into "
                       f"{tree}/{SOLUTION_DIR}/{solution.name}/",
            })
        # A helper nobody links to is a file the next run will not read.
        # A PROCEDURE written as prose is a tool that was not built.
        #
        # A fenced block in a solution is commands or code someone will run,
        # and prose is the expensive way to carry it: a tool costs one call,
        # while an instruction is read, interpreted and re-acted-on by every
        # task that loads the skill — differently each time, which is where
        # drift comes from. Measured: across every run to date the system
        # wrote lessons steadily and built ZERO tools, with `capability_new`
        # available throughout, because preferring a tool leaves the default
        # at prose and prose is always cheaper in the moment.
        #
        # Flagged only when nothing executable sits beside it, so a solution
        # that already built its tool is left alone.
        fenced = skill_text.count("```") >= 2
        has_tool = any(solution.glob("*.py"))
        if fenced and not has_tool:
            out.append({
                "path": f"{tree}/{SOLUTION_DIR}/{solution.name}/SKILL.md",
                "problem": "a procedure written as prose, with no tool beside it",
                "fix": "build the steps in the fenced block with "
                       "capability_new(category=...) and reference the tool "
                       "from the skill — a tool is called once; prose is "
                       "re-interpreted by every task that reads it",
            })

        # A `.py` beside the solution is that task's own fix, and belongs
        # here: the reader who loads the skill already is. Only SHARED tools
        # go to tools/<category>/.
        for helper in sorted(solution.glob("*.md")):
            if helper.name in ("SKILL.md", "LESSONS.md"):
                continue
            if helper.name not in skill_text:
                out.append({
                    "path": f"{tree}/{SOLUTION_DIR}/{solution.name}/{helper.name}",
                    "problem": "a helper note nothing links to",
                    "fix": f"link it from SKILL.md as [{helper.stem}]({helper.name}), "
                           f"or delete it — an unlinked note is never read",
                })

    for tool in sorted((base / TOOL_DIR).glob("*")):
        if tool.is_file():
            out.append({
                "path": f"{tree}/{TOOL_DIR}/{tool.name}",
                "problem": "a tool with no category",
                "fix": f"move it to {tree}/{TOOL_DIR}/<category>/{tool.name}",
            })
    return out


def register(mcp: Any) -> None:
    @mcp.tool()
    def layout_check(root: str = "") -> str:
        """Check that what you built is filed where the system will find it.

        **Call this before you finish.** A solution that is correct and
        misfiled is a solution nothing reuses, and nothing will tell you: the
        write succeeds and the next run's lookup just returns nothing.

        The layout, for both `capabilities/` (what a task NEEDED) and
        `research/` (what was SEARCHED FOR):

            <tree>/skills/<Name>/SKILL.md      the solution, plus helper
                                               notes LINKED from SKILL.md
            <tree>/tools/<category>/<name>.py  deterministic tools, grouped
                                               by what they are about

        Prefer a tool to an instruction wherever the steps are always the
        same: a tool costs one call, an instruction is re-read and
        re-interpreted by every task that loads the skill.

        Returns JSON: {status, ok, checked, issues: [{path, problem, fix}]}.
        Each issue names the move that fixes it, so act on them and call again.
        """
        from phronix.layers import layers

        roots = ([Path(root)] if root
                 else [Path(layer.root) for layer in layers()])
        issues: List[Dict[str, str]] = []
        checked: List[str] = []
        for base in roots:
            for tree in TREES:
                if (base / tree).is_dir():
                    checked.append(str(base / tree))
                    issues.extend(_issues_for(base, tree))
        return json.dumps({
            "status": "ok",
            "ok": not issues,
            "checked": checked,
            "issues": issues,
            "note": ("everything is filed correctly" if not issues else
                     "fix each `path` as its `fix` says, then call layout_check "
                     "again — a misfiled solution is never read"),
        }, indent=2)
