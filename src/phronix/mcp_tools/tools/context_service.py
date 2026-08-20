"""The two retrieval tool sets every agent starts from.

An agent facing a task needs two things, and they are different questions with
different homes in the schema:

**"How do I do this?"** → a **skill**: `SKILL.md`, holding Instructions (`I*`) and
Rules (`R*`) for exactly one subject.

**"What went wrong last time?"** → **memory**: a skill's `LESSONS.md` (Pitfalls
`P*`, Lessons `L*`) plus the standalone memory store.

They are separate tools rather than one search over everything, because mixed, the
stronger lexical match wins regardless of which question was asked — so a query
about how to run a migration returns the incident report from the last one, or
vice versa, and the agent proceeds with half of what it needed.

Skill retrieval is **index-first**, in two phases:

1. Match the query against each skill's subject, description and ``## Index``
   catalogue. This answers "which subject is this about?" without block bodies
   voting — a term appearing once in some paragraph must not make an unrelated
   subject look relevant.
2. Expand the query with the matched Index rows' own wording, then search *inside*
   those subjects with the graph. The index describes the subject in the skill's
   vocabulary, which is rarely the asker's; that expansion is the bridge.

Both return labelled blocks and exact sections, never whole files.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


def _graph_sections(query: str, store: str, subjects: List[str],
                    limit: int, max_lines: int) -> List[Dict[str, Any]]:
    """Phase two: graph search inside the subjects the index already chose.

    Best-effort. The index phase is a direct read of the store and is always
    current; the graph adds prose sections that are not labelled blocks. If
    ``graphify`` is unavailable or the graph is empty, retrieval degrades to the
    labelled blocks alone rather than failing — a partial answer beats an error.
    """
    if not subjects:
        return []
    try:
        from phronix.knowledge_graph import find_docs

        found = find_docs(query, store=store, limit=limit, max_lines=max_lines,
                          restrict_to=subjects)
    except Exception:
        return []
    if found.get("status") != "ok":
        return []
    return [
        {"skill": hit.get("artifact"), "heading": hit.get("heading"),
         "text": hit.get("text"), "source_file": hit.get("source_file"),
         "lines": hit.get("lines"), "score": hit.get("score")}
        for hit in found.get("results", [])
    ]


def register(mcp: Any) -> None:
    @mcp.tool()
    def context_skills(task: str, limit: int = 4, max_blocks: int = 4,
                       max_lines: int = 50) -> str:
        """Find HOW TO DO a task — the exact labelled blocks, never whole skills.

        **Call this first, before doing anything non-trivial.** A skill is verified
        learning about performing one specific subject: its Instructions (`I*`) say
        how, its Rules (`R*`) say what you must not do. Reasoning from model priors
        when a skill covers the task is the most common way a session repeats a
        mistake the project already solved.

        Search is index-first: it matches each skill's `## Index` catalogue to find
        the right *subject*, then looks inside that subject for the blocks that
        answer your question.

        What comes back, per matching skill:

        - `index_matches` — the catalogue rows that matched. Read these first; they
          are a map of the subject and cost almost nothing.
        - `blocks` — the labelled Instructions and Rules themselves, with their
          text. Each has a `label` you can cite or re-load with
          `skill_load(name=..., label="R3")`.
        - `sections` — additional prose located by the graph inside the same
          subject.
        - `has_lessons` — whether this subject also has recorded pitfalls. If so,
          call `context_memory` on the same topic: the rules tell you what to do,
          the lessons tell you what bit someone last time.

        **Follow the references.** A block may cite `[[other-skill#R2]]`. Each skill
        covers one subject only, so anything it needs from another subject is a
        link rather than a copy — the link is not optional reading.

        Args:
            task: what you are about to do, in your own words. An error message
                works too.
            limit: how many subjects to return.
            max_blocks: how many labelled blocks per subject.
            max_lines: truncate any graph-located section longer than this.

        Returns JSON: {status, query, count, results: [{skill, subject, layer,
        description, index_matches, blocks, sections, has_lessons}]}.
        """
        from phronix.skills import search

        try:
            found = search(task, max_results=limit, max_blocks=max_blocks)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        if found.get("status") != "ok":
            return json.dumps(found, indent=2)

        subjects = [r["skill"] for r in found["results"]]
        sections = _graph_sections(task, "skills", subjects, limit * 2, max_lines)
        by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for section in sections:
            by_skill.setdefault(str(section["skill"]), []).append(section)
        for result in found["results"]:
            result["sections"] = by_skill.get(result["skill"], [])

        found["usage"] = ("skill_load(name=..., label='R3') for one block; "
                          "context_memory(topic=...) for what went wrong before.")
        return json.dumps(found, indent=2)

    @mcp.tool()
    def context_memory(topic: str, limit: int = 6, max_lines: int = 50,
                       expand_links: bool = True) -> str:
        """Find WHAT WENT WRONG before — pitfalls, lessons, and durable facts.

        **Call this alongside `context_skills`, before acting.** This is the other
        half of the context: the traps, the dated symptom → root cause → exact fix
        entries, the decisions and standing guidance from past sessions. A skill
        tells you the procedure; memory tells you what the procedure does not
        mention.

        Two sources, both searched:

        - **Skill lessons** — each subject's `LESSONS.md`, holding Pitfalls (`P*`)
          and Lessons (`L*`). Deliberately a separate file from `SKILL.md` so that
          asking "how do I do this" does not drag in every past incident.
        - **The memory store** — standalone durable facts, decisions and user
          guidance, with one hop of `[[wikilink]]` expansion.

        The `linked` entries were pulled in by a wikilink rather than by matching
        your query. Read them: they are usually the constraint you did not know to
        ask about.

        Args:
            topic: the subject you are working on, an error message, or a decision
                you are about to make.
            limit: how many entries per source.
            max_lines: truncate any single entry longer than this.
            expand_links: include 1-hop [[wikilink]] neighbours from the store.

        Returns JSON: {status, topic, lessons: [...], memories: [...], linked: [...]}.
        """
        from phronix.memory_graph import recall, render_digest
        from phronix.skills import search

        payload: Dict[str, Any] = {"status": "ok", "topic": topic}

        # Skill lessons, found through the same index-first phase so the pitfalls
        # come from the subject the question is actually about.
        try:
            hit = search(topic, max_results=limit, max_blocks=limit,
                         kinds=["lesson", "pitfall"])
            subjects = [r["skill"] for r in hit.get("results", [])]
            payload["lessons"] = [
                {"skill": r["skill"], "subject": r["subject"],
                 "entries": [b for b in r["blocks"]]}
                for r in hit.get("results", []) if r["blocks"]
            ]
            payload["lesson_sections"] = _graph_sections(
                topic, "lessons", subjects, limit, max_lines)
        except Exception as exc:
            payload["lessons"] = []
            payload["lessons_error"] = f"{type(exc).__name__}: {exc}"

        # The standalone memory store.
        try:
            ranked = recall(topic, k=limit, expand_links=expand_links)
            payload["memories"] = [r for r in ranked if r["via"] == "match"]
            payload["linked"] = [r for r in ranked if r["via"] != "match"]
            payload["digest"] = render_digest(ranked, budget_chars=2000)
        except Exception as exc:
            payload["memories"] = []
            payload["memories_error"] = f"{type(exc).__name__}: {exc}"

        if not payload.get("lessons") and not payload.get("memories"):
            payload["status"] = "no_match"
        payload["usage"] = ("memory_read(name=...) for a full memory; "
                            "skill_load(name=..., file='LESSONS.md') for a whole lessons file; "
                            "skill_write_lesson(...) to record what THIS session learns.")
        return json.dumps(payload, indent=2)

    @mcp.tool()
    def context_for_task(task: str, limit: int = 3, max_lines: int = 40) -> str:
        """Both halves of the context for a task, in one call.

        How to do it (skills: Instructions and Rules) and what went wrong before
        (memory: Pitfalls and Lessons). Use this to open a task; use the individual
        tools when you need to dig further into one side.

        Returns JSON: {status, task, skills, memory, verification}. ``verification``
        names the subjects involved that have no corrector behind them — guidance
        that has never been falsified, to be treated with more caution and worth
        closing before you finish.
        """
        from phronix.skills import search
        from phronix.verification import covers

        try:
            skills_hit = search(task, max_results=limit, max_blocks=limit)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

        subjects = [r["skill"] for r in skills_hit.get("results", [])]
        unverified = [s for s in subjects if not covers("skill", s)]

        memory: Dict[str, Any] = {}
        try:
            from phronix.memory_graph import recall

            lessons = search(task, max_results=limit, max_blocks=limit,
                             kinds=["lesson", "pitfall"])
            memory = {
                "lessons": [{"skill": r["skill"], "entries": r["blocks"]}
                            for r in lessons.get("results", []) if r["blocks"]],
                "memories": recall(task, k=limit),
            }
        except Exception as exc:
            memory = {"error": f"{type(exc).__name__}: {exc}"}

        return json.dumps({
            "status": "ok",
            "task": task,
            "skills": skills_hit,
            "memory": memory,
            "verification": {
                "unverified_subjects": unverified,
                "note": ("These subjects have no authored corrector, so their claims have "
                         "never been falsified. Treat them as informed guidance rather than "
                         "established fact, and consider closing the gap with verify_new."),
            },
        }, indent=2)
