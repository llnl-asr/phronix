"""Declarative, idempotent authoring for skills and agents.

The incremental writers (``skill_write``, ``skill_write_lesson``) add one thing per
call: they allocate a new label each time, so re-running one appends rather than
converging. That is right for "record what I just learned" and wrong for "make
this artifact correct".

These two tools are the declarative counterpart. You pass the *whole* intended
structure; the tool renders it deterministically and writes it only if the bytes
differ. Same input, same file, on any machine, from any prior state — so an agent
that is unsure whether it already ran one can simply run it again.

Both enforce the required structure before writing and report the built-in
structural corrector's verdict with the result, so a malformed artifact is caught
at authoring time rather than becoming a file that misbehaves quietly later.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def register(mcp: Any) -> None:
    @mcp.tool()
    def skill_define(
        name: str,
        description: str,
        subject: str = "",
        instructions: Optional[List[Dict[str, str]]] = None,
        rules: Optional[List[Dict[str, str]]] = None,
        references: Optional[List[Dict[str, str]]] = None,
        pitfalls: Optional[List[Dict[str, str]]] = None,
        lessons: Optional[List[Dict[str, str]]] = None,
        kind: str = "skill",
        subjects: str = "",
        layer: str = "",
        allow_relabel: bool = False,
    ) -> str:
        """Create or update a skill declaratively, in the required structure. Idempotent.

        **Use this to state what a skill should BE.** The arguments fully determine
        the file: the Index is generated, sections are emitted in a fixed order,
        blocks not listed are removed, and the output is byte-identical for the
        same input. Re-running reports `unchanged` and writes nothing — so it is
        always safe to run again if you are unsure whether it took effect.

        (`skill_write` is the other mode: it appends ONE block per call and cannot
        be re-run safely. Use it to record a single new thing; use this to author
        or restructure.)

        Each block entry is `{"title": ..., "body": ...}`, optionally with an
        explicit `"label"`:

        - `instructions` → `I*` — steps, in order. How to do the thing.
        - `rules` → `R*` — constraints. What you must or must not do, and why.
        - `references` → `X*` — links into other subjects' blocks, with the reason.
        - `pitfalls` → `P*` and `lessons` → `L*` — these go to `LESSONS.md`, and are
          retrieved by `context_memory` rather than by skill search.

        **Structure rules this enforces:**

        - **One skill, one subject.** If your content spans two, define the second
          subject separately and link them. A skill covering two becomes findable
          for neither, because retrieval matches the subject first.
        - **A skill needs at least one instruction or rule.** One with neither says
          nothing about how to do anything.
        - **3C — clear, concise, constrained.** One idea per block. State the rule
          before the rationale. Title it with what someone would search for.
        - Set `kind="association"` with `subjects="a, b"` for a join skill holding
          only the links between two subjects and what is true of the combination.

        **Labels are stable.** A block keeps its label across updates when its title
        is unchanged, so editing a body never renumbers anything. Pass an explicit
        `label` to pin one. If an update would drop a label that another skill
        cites, the call is REFUSED and tells you who cites it — a dangling foreign
        key is worse than a rejected edit, because nothing downstream reports it.
        Override with `allow_relabel=True` only after updating the citing skills.

        **Omitting `lessons`/`pitfalls` does not delete them.** Recorded lessons are
        the most expensive content in the store to reproduce, and a caller that
        simply did not pass the argument did not mean "discard everything anyone
        learned here". Pass them explicitly to replace them.

        Args:
            name: kebab-case slug, also the directory name.
            description: one or two sentences — what this subject is and when to
                load it. This is the main retrieval signal; be specific.
            subject: the single subject covered (defaults to the name).
            instructions/rules/references/pitfalls/lessons: block lists.
            kind: "skill" or "association".
            subjects: for an association, the comma-separated pair it joins.
            layer: force a target layer ("project", "user", "bundled").
            allow_relabel: proceed even if a cited label disappears.

        Returns JSON: {status, action, skill, layer, files_written, labels,
        corrector, verification}. ``action`` is created | updated | unchanged.
        ``corrector`` is the structural verdict — read its findings before moving
        on. ``labels`` maps each label to its title, for citing from elsewhere.
        """
        from phronix.skills import define

        try:
            return json.dumps(define(
                name, description, subject=subject,
                instructions=instructions, rules=rules, references=references,
                pitfalls=pitfalls, lessons=lessons, kind=kind,
                subjects=[s.strip() for s in subjects.split(",") if s.strip()],
                layer=layer or None, allow_relabel=allow_relabel,
            ), indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

    @mcp.tool()
    def agent_define(
        name: str,
        description: str,
        model_level: str,
        sections: List[Dict[str, str]],
        tools: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        effort: str = "",
        isolation: str = "",
        layer: str = "",
        sync: bool = True,
    ) -> str:
        """Create or update an agent template declaratively, and re-render it. Idempotent.

        **Use this instead of editing agent files.** The rendered per-harness files
        (`.claude/agents/*.md`, `.opencode/agents/*.md`, `.github/agents/*.agent.md`,
        `.codex/agents/*.toml`) are build artifacts — an edit there is silently
        reverted by the next sync. This writes the one harness-neutral template and
        re-renders all four.

        The same arguments produce a byte-identical template, so re-running reports
        `unchanged` and writes nothing.

        **`sections`** entries are either:

        - `{"include": "self-learning"}` — pull in a shared section from the common
          library, so a standing rule stays a one-file edit; or
        - `{"title": ..., "body": ...}` — prose specific to this agent.

        Includes are validated before anything is written: an unresolved one breaks
        rendering for all four harnesses at once, and discovering that at sync time
        means the authoring session has already ended.

        **`model_level`** is a capability level, never a model id:

        | Level | For |
        |---|---|
        | `level_1` | deterministic orchestration and tool plumbing |
        | `level_2` | routing, planning, limited reasoning |
        | `level_3` | analysis, diagnosis, stage-to-stage decisions |
        | `level_4` | deep synthesis and cross-cutting reasoning |

        The indirection is what lets one definition run everywhere and makes a model
        upgrade a one-line edit in `models.yaml`.

        **`description` is the dispatch signal** — it is how a router decides to use
        this agent. State what it does AND when to reach for it. "Reviews code" is
        unusable; "Reviews changed code for reuse and simplification; use after a
        feature lands, not for bug hunting" is dispatchable.

        **`tools`** should list only what the agent needs. Every tool schema sits in
        context for the whole session, and an agent with fifty tools reaches for the
        wrong one. Use neutral names (`Read`, `Bash`, `mcp__phronix__skill_load`);
        the converters reshape them per harness.

        **`skills`** must name skills that exist — otherwise the agent is told to
        load something that is not there, and behaves as if the guidance were simply
        absent. This is checked before writing.

        Args:
            name: kebab-case slug, also the filename stem.
            description: what it does and when to dispatch to it.
            model_level: level_1 … level_4.
            sections: the ordered prompt body.
            tools: neutral tool names to allow.
            skills: skills the agent should load.
            effort: reasoning-effort hint (claude/codex; others ignore it).
            isolation: e.g. "worktree" (claude-only hint).
            layer: force a target layer.
            sync: re-render all four harnesses afterwards.

        Returns JSON: {status, action, agent, layer, file, corrector, sync, next}.
        Changing how an existing agent behaves needs the user's confirmation — an
        agent that quietly acquired a wrong rule is very hard to debug, because
        nothing in its output says which rule caused it.
        """
        from phronix.agents import define_agent

        try:
            return json.dumps(define_agent(
                name, description, model_level, sections,
                tools=tools, skills=skills, effort=effort, isolation=isolation,
                layer=layer or None, sync=sync,
            ), indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
