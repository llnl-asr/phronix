"""Skill tools: reading and growing the relational skill store.

Claude Code discovers skills natively from ``.claude/skills/``. OpenCode, Copilot
and Codex do not — which is why these exist. They give every harness the same
operations over the same merged library, so a skill written in a Claude session is
usable from Codex with nothing copied or converted.

Prefer ``context_skills`` for retrieval: it is index-first and returns the exact
blocks. These tools are for when you already know the subject and want a specific
labelled block, or when you are writing one.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional


def register(mcp: Any) -> None:
    @mcp.tool()
    def skill_list() -> str:
        """List every subject the library covers, with its block counts and layer.

        One skill = one subject. Use this to see the shape of the library; use
        ``context_skills`` to actually find something, and ``skill_index`` to see
        inside one subject without loading it.

        ``type`` is ``skill`` for a subject, or ``association`` for a join skill
        that holds only what is true of a *pair* of subjects.

        Returns JSON: {status, count, skills: [{name, subject, type, layer,
        description, instructions, rules, references, lessons}]}.
        """
        from phronix.skills import iter_skills

        skills = [
            {
                "name": s["name"],
                "subject": s.get("subject") or s["name"],
                "type": s.get("type", "skill"),
                "layer": s["layer"],
                "description": s["description"],
                "instructions": sum(1 for b in s["blocks"] if b["kind"] == "instruction"),
                "rules": sum(1 for b in s["blocks"] if b["kind"] == "rule"),
                "references": sum(1 for b in s["blocks"] if b["kind"] == "reference"),
                "lessons": len(s["lesson_blocks"]),
            }
            for s in iter_skills()
        ]
        return json.dumps({
            "status": "ok", "count": len(skills), "skills": skills,
            "usage": "context_skills(task=...) to find one; skill_index(name=...) to see "
                     "inside it; skill_load(name=..., label='R3') for one block.",
        }, indent=2)

    @mcp.tool()
    def skill_index(name: str) -> str:
        """Show one subject's `## Index` catalogue — the cheapest way to look inside.

        The Index maps every label to its section and what it covers. Reading it
        costs a few hundred tokens and tells you exactly which block to load, which
        is why retrieval matches against it before it looks at any content.

        Returns JSON: {status, skill, subject, type, description, index:
        [{label, section, covers}], has_lessons}.
        """
        from phronix.skills import index_of

        return json.dumps(index_of(name), indent=2)

    @mcp.tool()
    def skill_search(query: str, max_results: int = 5, max_blocks: int = 4) -> str:
        """Index-first search over subjects, returning labelled blocks.

        The same engine ``context_skills`` uses. Prefer ``context_skills`` in
        normal work — it also pulls in graph-located prose and tells you whether
        the subject has recorded pitfalls.

        Returns JSON: {status, query, count, results: [{skill, subject, score,
        index_matches, blocks}]}.
        """
        from phronix.skills import search

        return json.dumps(search(query, max_results=max_results,
                                 max_blocks=max_blocks), indent=2)

    @mcp.tool()
    def skill_load(name: str, label: str = "", section: str = "",
                   file: str = "SKILL.md") -> str:
        """Load a skill: one labelled block, one section, or the whole file.

        **Pass ``label`` whenever you can.** ``R3`` returns exactly one constraint;
        that is what makes partial loading real rather than aspirational. Use
        ``section`` for a whole group (all Rules). Load a whole file only when you
        genuinely need every part of it — an exhaustive checklist walk, say.

        Accepts a comma-separated list of names to load several at once.

        Args:
            name: skill name (or comma-separated names).
            label: a block label — `I1`, `R2`, `X1`, `P1`, `L4`.
            section: a `## ` heading, or a substring of one.
            file: "SKILL.md" (instructions and rules) or "LESSONS.md" (pitfalls and
                lessons), or a sibling reference file in the skill's directory.

        Returns JSON: {status, loaded: [{skill, layer, label, kind, title, content,
        references}], missing: [...]}. ``references`` are the `[[skill#LABEL]]`
        foreign keys in the text returned — each skill covers one subject, so
        anything from another subject is a link rather than a copy, and the link is
        not optional reading.
        """
        from phronix.skills import load

        return json.dumps(load(name, label=label, section=section, file=file), indent=2)

    @mcp.tool()
    def skill_create(name: str, description: str, subject: str = "",
                     kind: str = "skill", subjects: str = "", layer: str = "") -> str:
        """Create a new subject, or an association skill joining two subjects.

        **One skill covers ONE subject.** If what you are recording spans two, do
        not widen an existing skill — create the second subject and link them.
        When the two genuinely interact in ways neither owns alone, create an
        `association` skill: it holds only the references between their blocks and
        the rules that are true of the combination.

        That is the whole discipline. A skill that grows a second subject stops
        being findable for either.

        Args:
            name: kebab-case slug, which is also the directory name.
            description: one or two sentences — what this subject is and when to
                load it. This is the main retrieval signal; make it specific.
            subject: the single subject covered (defaults to the name).
            kind: "skill" or "association".
            subjects: for an association, the comma-separated pair it joins.
            layer: force a target layer ("project", "user", "bundled").

        Returns JSON: {status, skill, type, layer, file, next}.
        """
        from phronix.skills import create

        pair = [s.strip() for s in subjects.split(",") if s.strip()]
        return json.dumps(create(name, description, subject=subject, kind=kind,
                                 subjects=pair, layer=layer or None), indent=2)

    @mcp.tool()
    def skill_write(skill: str, kind: str, title: str, body: str,
                    description: str = "", layer: str = "") -> str:
        """Add an Instruction, Rule or Reference block to a subject.

        This is how a skill grows on the "how to do it" side. Choose the kind by
        what the content IS:

        - `instruction` (`I*`) — a step, in order. How to do the thing.
        - `rule` (`R*`) — a constraint. What you must or must not do, and why.
        - `reference` (`X*`) — a link into another subject's block, with the reason
          the link exists.

        A **pitfall or a dated lesson is not any of these** — it goes to
        `skill_write_lesson`, which files it in `LESSONS.md`. Keeping them apart is
        what lets "how do I do this" and "what went wrong last time" be answered
        separately instead of dragging in each other.

        **3C — clear, concise, constrained.** One idea per block. State the rule
        before the rationale. If you find yourself writing about a second subject,
        stop and link to it with `[[other-skill#R2]]` instead.

        The label is allocated automatically and never recycled: a reused label
        would silently redirect every existing reference to different content. The
        Index is regenerated so the catalogue cannot drift from the content.

        Args:
            skill: the subject to add to; created if it does not exist.
            kind: instruction | rule | reference.
            title: a short, specific heading — this is what the Index shows and
                what search matches first.
            body: the content. Keep it to one idea.
            description: used only when creating a new skill.
            layer: force a target layer ("project", "user", "bundled").

        Returns JSON: {status, action, skill, label, kind, file, layer, reference,
        verification}. ``reference`` is the `[[skill#LABEL]]` other skills should
        use to cite this block. ``verification`` says whether a corrector covers
        this subject — write one with `verify_new` if not.
        """
        from phronix.skills import write_block

        return json.dumps(write_block(skill, kind, title, body,
                                      description=description, layer=layer or None),
                          indent=2)

    @mcp.tool()
    def skill_write_lesson(skill: str, lesson: str, kind: str = "lesson",
                           title: str = "", description: str = "",
                           layer: str = "") -> str:
        """Record a pitfall or a dated lesson into a subject's `LESSONS.md`.

        **This is the self-learning write path — use it before you finish, every
        session.** Whenever something non-obvious happened, capture it as
        *symptom → root cause → exact fix*. A lesson kept in your head is one the
        next session pays for again.

        Two kinds:

        - `pitfall` (`P*`) — a trap and how to avoid it. Timeless: it describes a
          hazard that is always there.
        - `lesson` (`L*`) — a dated incident. What broke, why, and the exact fix.

        These land in `LESSONS.md`, not `SKILL.md`, and are retrieved by
        `context_memory` rather than `context_skills`. If what you learned changes
        the *procedure*, also add or amend an Instruction or Rule with
        `skill_write` — the lesson records what happened, the rule prevents it.

        Content is redacted before it lands, because this file is committed and
        shared. What was stripped comes back in `redacted`.

        Args:
            skill: the subject it belongs to; created if it does not exist.
            lesson: the entry. Lead with the symptom as it actually appears — that
                is what the next person will search for.
            kind: "lesson" or "pitfall".
            title: a short heading; derived from the text when omitted.
            description: used only when creating a new skill.
            layer: force a target layer.

        Returns JSON: {status, action, skill, label, kind, file, layer, reference,
        redacted, verification}.
        """
        from phronix.skills import write_lesson

        return json.dumps(write_lesson(skill, lesson, kind=kind, title=title,
                                       description=description, layer=layer or None),
                          indent=2)
