"""Solution: is this skill one a later run can actually act on?

`layout_check` asks whether a solution is filed where it will be found, and
`research_validate` asks whether the research record is usable. Neither asks
the question that decides whether reuse works: does the solution CARRY the fix,
or does it only describe one?

That distinction was measured across five tasks. The one skill holding a real
diff is the one task that passes in every reuse run; the four holding prose
produce a different result each time. A skill that says "replace iter_content
with iter_lines" is a hint. A skill carrying the diff is an answer.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

#: A block title must not carry the label the renderer adds.
LABEL_IN_TITLE = re.compile(r"^\s*[A-Z]{1,2}\d+\s*[—–-]\s*")

#: What the harness writes when a task has nothing established yet.
PLACEHOLDER = "Nothing is established about this subject yet"

#: Enough of a description to be a retrieval signal rather than a name.
MIN_DESCRIPTION = 40


def check_skill(home: Path) -> List[Dict[str, str]]:
    """Everything wrong with one solution skill, each with the move that fixes it."""
    from phronix import skill_schema

    out: List[Dict[str, str]] = []

    def flag(problem: str, fix: str) -> None:
        out.append({"skill": home.name, "problem": problem, "fix": fix})

    if not (home / "SKILL.md").is_file():
        flag("no SKILL.md", "write the solution with skill_write")
        return out
    try:
        parsed = skill_schema.parse_skill(home)
        text = (home / "SKILL.md").read_text(errors="replace")
    except Exception as exc:
        flag(f"SKILL.md does not parse: {type(exc).__name__}",
             "rewrite it with skill_write rather than editing the file by hand")
        return out

    blocks = list(parsed.get("blocks") or [])
    real = [b for b in blocks
            if str(b.get("title") or "").strip() != PLACEHOLDER]

    if not real:
        flag("nothing established — the placeholder is all there is",
             "this is only a problem once the task has been attempted; "
             "record what was tried and what it cost")

    # The whole point: does it carry the fix, or describe one?
    carries_diff = ("@@" in text or "--- a/" in text or "+++ b/" in text)
    names_a_file = bool(re.search(r"[\w/]+\.(py|c|h|js|ts|rs|go)\b", text))
    if real and not carries_diff:
        flag("describes a fix but carries no diff",
             "put the patch that passed into the skill verbatim — a later run "
             "reading prose has to re-derive the change, and re-derivation is "
             "where a reproducible pass turns back into a coin flip"
             + ("" if names_a_file else
                "; it does not even name a source file"))

    if real and carries_diff and not names_a_file:
        flag("has a diff that names no file",
             "a hunk with no file path cannot be applied; include the "
             "`--- a/<path>` and `+++ b/<path>` lines")

    for block in blocks:
        title = str(block.get("title") or "")
        if LABEL_IN_TITLE.match(title):
            flag(f"block title carries its own label: {title[:48]!r}",
                 "the renderer adds the label; a title holding one creates a "
                 "duplicate the same-point merge cannot see")

    seen: Dict[str, int] = {}
    for block in real:
        key = LABEL_IN_TITLE.sub("", str(block.get("title") or "")).strip().lower()
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            flag(f"{count} blocks make the same point: {key[:48]!r}",
                 "merge them — two blocks for one point split every read")

    if real and any(str(b.get("title") or "").strip() == PLACEHOLDER
                    for b in blocks):
        flag("says nothing is established, and establishes something",
             "drop the placeholder rule: a skill that hands over an answer and "
             "also denies having one is worse than either alone")

    description = str(parsed.get("description") or "")
    if "Nothing yet" in description or len(description.strip()) < MIN_DESCRIPTION:
        flag(f"description is {len(description.strip())} chars",
             "the description is the main retrieval signal — say what the "
             "skill knows, not that it exists")
    return out


def register(mcp: Any) -> None:
    @mcp.tool()
    def solution_check(skill: str = "") -> str:
        """Is this solution one a later run can act on, or only read?

        **Call this on the skill you just wrote.** `layout_check` says whether
        it is filed correctly and `research_validate` says whether the record
        is usable; this says whether the solution CARRIES the fix.

        The distinction decides whether reuse works. Measured across five
        tasks: the one skill holding a real diff is the one task that passes
        in every reuse run, and the four holding prose produce a different
        result each time. "Replace `iter_content` with `iter_lines`" is a
        hint; the diff is an answer.

        Also catches a title carrying its own label (which creates a duplicate
        the merge cannot see), two blocks making one point, a placeholder left
        beside real content, and a description too thin to retrieve on.

        Pass `skill` to check one, or omit it to check every solution visible
        here. Returns JSON: {status, ok, checked, issues: [{skill, problem,
        fix}]}.
        """
        from phronix.layers import layers

        homes: List[Path] = []
        for layer in layers():
            for tree in ("capabilities", "research"):
                base = Path(layer.root) / tree / "skills"
                if not base.is_dir():
                    continue
                for entry in sorted(base.iterdir()):
                    if entry.is_dir() and (not skill or entry.name == skill):
                        homes.append(entry)

        issues: List[Dict[str, str]] = []
        for home in homes:
            issues.extend(check_skill(home))
        return json.dumps({
            "status": "ok",
            "ok": not issues,
            "checked": [h.name for h in homes],
            "issues": issues,
            "note": ("every solution carries its fix" if not issues else
                     "fix each `skill` as its `fix` says, then call again"),
        }, indent=2)
