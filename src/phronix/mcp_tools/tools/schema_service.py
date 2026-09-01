"""Schema: is the research record something a later run can act on?

A record is not a diary. It is read by the next attempt on this subject, which
arrives asking three questions — what was tried, what happened, and what is
still open — and can only answer them from what is written down in a shape it
can read.

Every field here exists because its absence cost something. A metric with no
`measurement` is a prediction being read as a result. An approach with no
`hypothesis` cannot be falsified, so nothing it "showed" means anything. A
`chosen` approach that is not in `approaches` is a plan pointing at nothing.

So the record is checked, and the check names the fix rather than the fault.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

#: A record must have these to be a record at all.
REQUIRED = ("topic", "slug", "approaches", "plan")

#: An approach must have these to be judgeable.
APPROACH_REQUIRED = ("name", "summary", "hypothesis")


def _check(record: Dict[str, Any]) -> List[Dict[str, str]]:
    """Everything wrong with one record, each with the move that fixes it."""
    out: List[Dict[str, str]] = []

    def flag(where: str, problem: str, fix: str) -> None:
        out.append({"where": where, "problem": problem, "fix": fix})

    for key in REQUIRED:
        if key not in record:
            flag(key, "missing from the record",
                 f"`{key}` is what makes this a record; "
                 f"call the research tool that sets it")

    approaches = record.get("approaches") or []
    if not isinstance(approaches, list):
        flag("approaches", "not a list", "it holds one entry per approach tried")
        return out

    names = set()
    for index, entry in enumerate(approaches):
        label = f"approaches[{index}]"
        if not isinstance(entry, dict):
            flag(label, "not an object", "each approach is a record of its own")
            continue
        name = str(entry.get("name") or "")
        label = f"approaches[{name or index}]"
        if name in names:
            flag(label, "two approaches share a name",
                 "rename one — a later run cannot tell which result is which, "
                 "and the record reads as two findings where there is one")
        names.add(name)

        for key in APPROACH_REQUIRED:
            if not str(entry.get(key) or "").strip():
                flag(label, f"no `{key}`",
                     "an approach with no hypothesis cannot be falsified, so "
                     "nothing it shows means anything"
                     if key == "hypothesis" else
                     f"set `{key}` when you record the approach")

        metrics = entry.get("metrics") or {}
        if metrics and not str(entry.get("measurement") or "").strip():
            flag(label, "has metrics but no `measurement`",
                 "say HOW the numbers were obtained, or record them as a "
                 "prediction — an unmeasured number read as a result is the "
                 "difference between a comparison and a rationalisation")
        if entry.get("measured") and not metrics:
            flag(label, "marked measured with no metrics",
                 "record what was measured, or clear `measured`")

        status = str(entry.get("status") or "")
        if status in ("confirmed", "falsified") and not metrics:
            flag(label, f"status `{status}` with nothing behind it",
                 "a verdict needs the measurement that produced it")

    chosen = record.get("chosen")
    if chosen and str(chosen) not in names:
        flag("chosen", f"`{chosen}` is not one of the approaches",
             "the plan points at an approach that is not in the record; "
             "add it, or choose one that is there")

    fom = record.get("fom")
    if approaches and not fom:
        flag("fom", "no figure of merit",
             "approaches cannot be ranked against each other without one — "
             "fix it BEFORE measuring, or the winner is chosen after the fact")

    plan = record.get("plan") or []
    for index, step in enumerate(plan):
        if not isinstance(step, dict):
            continue
        kind = str(step.get("kind") or "")
        if kind == "deterministic" and not str(step.get("capability") or "").strip():
            flag(f"plan[{index}]", "a deterministic step with no capability",
                 "build it with capability_new and name it here — a "
                 "deterministic step written as prose is re-interpreted by "
                 "every run that reads it")
        if not str(step.get("title") or "").strip():
            flag(f"plan[{index}]", "a step with no title",
                 "say what the step does")
    return out


def register(mcp: Any) -> None:
    @mcp.tool()
    def research_validate(topic: str = "") -> str:
        """Check that the research record is one a later run can act on.

        **Call this before you finish, and fix what it returns.** The record is
        read by the next attempt on this subject, which arrives asking what was
        tried, what happened, and what is still open. A record that cannot
        answer those has cost its whole price and bought nothing.

        What it checks, and why each matters:

        * every approach has a `hypothesis` — one that cannot be falsified
          means nothing it "showed" counts;
        * metrics come with a `measurement` — an unmeasured number read as a
          result is the difference between a comparison and a rationalisation;
        * a `chosen` approach actually exists in the record;
        * a figure of merit was fixed, so the winner is not chosen after the
          fact;
        * a deterministic plan step names the capability that runs it.

        Returns JSON: {status, ok, topic, checked, issues: [{where, problem,
        fix}]}. Act on each `fix` and call again.
        """
        from phronix import research

        topics = [topic] if topic else research.list_topics()
        issues: List[Dict[str, str]] = []
        checked: List[str] = []
        for name in topics:
            record = research.status(name) if hasattr(research, "status") else None
            if not isinstance(record, dict):
                continue
            checked.append(name)
            for issue in _check(record):
                issues.append({**issue, "topic": name})
        return json.dumps({
            "status": "ok",
            "ok": not issues,
            "checked": checked,
            "issues": issues,
            "note": ("the record is complete" if not issues else
                     "fix each `where` as its `fix` says, then call "
                     "research_validate again"),
        }, indent=2)
