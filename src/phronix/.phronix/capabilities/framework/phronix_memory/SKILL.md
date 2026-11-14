---
name: phronix_memory
description: Decide whether something belongs in memory or a skill, pick the memory type (project, feedback, reference, lesson), write a description that retrieves, link it with [[wikilinks]], and choose the layer that should inherit it. Load before recording a durable fact, a decision or user guidance, or when wondering why a memory was never surfaced ('memory not injected', 'type: user rejected', a feedback memory without Why).
---
Cross-references: [[knowledge]], [[lessons]], [[phronix_privacy]], [[phronix_context_economy]], [[phronix_skill_authoring]], [[phronix_self_learning]]

# Memory: the durable store of facts, decisions and guidance

Converted from the dftracer-agents skill `phronix-memory` (subject: the durable memory store of facts, decisions and guidance). Source description: What belongs in memory versus a skill, the four memory types and when to use each, writing descriptions that retrieve, wikilinks, and how memory reaches the model automatically. Load before recording a durable fact or wondering why a memory was never surfaced.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** knowledge's `memory_write` is this store in the capability world, and its Constraints repeat R1/R2 (a feedback memory needs Why and How to apply; one fact per memory; writing the same name updates it); knowledge's Rules 'Where a fact goes' is I1. Pitfalls about a subject go to that capability's LESSONS.md via `lesson_add` (lessons). Candidate to merge into knowledge.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Choose memory or a skill |
| `I2` | Instructions | Pick the type by what the fact is |
| `I3` | Instructions | Write a description that retrieves |
| `I4` | Instructions | Link liberally |
| `R1` | Rules | A `feedback` memory without a Why is incomplete |
| `R2` | Rules | Names are stable slugs; writing the same name updates |
| `R3` | Rules | Memory is committed and shared |
| `R4` | Rules | The write layer decides who inherits the memory |
| `R5` | Rules | Injection is tiered and deduplicated by design |
| `X1` | References | Where lessons about a subject go instead |
| `X2` | References | How memory is retrieved |

## Instructions

### I1 — Choose memory or a skill

A **skill** answers *"how do I do X?"* — procedures, constraints. A **memory**
answers *"what is true here?"* — decisions, constraints, state, guidance.

"Postgres 14 needs this flag for parallel restore" is a skill. "We chose Postgres
over MySQL for the extension ecosystem" is a memory. "Always ask before running a
migration on staging" is a memory.

### I2 — Pick the type by what the fact is

| Type | For | Must include |
|---|---|---|
| `project` | ongoing work, goals, constraints not derivable from the code | current state, what "done" means |
| `feedback` | the user's guidance on how to work | **Why:** and **How to apply:** |
| `reference` | pointers to external resources | what the resource is for |
| `lesson` | symptom → root cause → exact fix | the symptom as it actually appears |

### I3 — Write a description that retrieves

It is what the index shows and what gets injected into prompts, so it carries most
of the retrieval signal. Write a specific sentence, not a label: "Auth work"
retrieves for nothing; "Migrating session auth to short-lived JWTs; blocked on the
refresh-token rotation design" retrieves for four different queries.

Convert relative dates to absolute — "last week" is meaningless in three months.

### I4 — Link liberally

Retrieval walks one hop of the `[[wikilink]]` graph, so a memory that scores well
pulls in its neighbours even when their text does not match the query. That is how
a question about "the migration" surfaces the standing rule about migration
approvals, which contains none of the query's words.

A link to a memory that does not exist yet is not an error; it marks one worth
writing.

## Rules

### R1 — A `feedback` memory without a Why is incomplete

A rule without its rationale gets misapplied the first time the situation differs
from the one that produced it — and nobody can tell whether it still applies, so it
is either followed forever or dropped entirely.

### R2 — Names are stable slugs; writing the same name updates

That is the intent: a memory's job is to hold the *current* truth about something,
not to accumulate versions of it.

### R3 — Memory is committed and shared

Same rules as every other persisted artifact: see [[phronix-privacy#R1]].
`type: user` is rejected outright.

### R4 — The write layer decides who inherits the memory

`project` (`<repo>/.phronix/memory/`) reaches everyone who clones the repo; `user`
(`~/.phronix/memory/`) reaches only you; `bundled` reaches everyone who installs
phronix. `phronix_status()` shows the active target.

### R5 — Injection is tiered and deduplicated by design

The standing rules go in once per session and each memory once per session; when
nothing new is relevant, nothing is injected. A session issues hundreds of tool
calls, and repeating the same digest on each would cost six figures of tokens in
text the model has already seen — while crowding out the work.

### Using the tools (capability)

- Render the procedure with `phronix_memory_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `name`, `type`, `description`, `body`, `links`, `layer`) to `phronix_memory_check`; a step is done only when the check passes.

## References

### X1 — Where lessons about a subject go instead

A pitfall or dated incident about a specific subject belongs in that skill's
LESSONS.md, not the memory store: [[phronix-skill-authoring#R4]].

### X2 — How memory is retrieved

[[phronix-context-economy#I1]].

## Constraints

- Never write type: user: no redaction makes a profile of a person safe (R3, phronix-privacy R2).
- Never write a memory for what the code or a capability already records (knowledge Constraints).
- One fact per memory; the same name updates it (R2).
- Everything written here is committed and shared: privacy rules apply before writing (R3).

## Corner cases

- A link to a memory that does not exist yet is not an error: it marks one worth writing (I4).
- A memory that scores well pulls in its one-hop neighbours even when their text does not match the query: that is how 'the migration' surfaces the migration-approval rule (I4).
- When nothing new is relevant nothing is injected; repeating the digest on every tool call would cost six figures of tokens (R5).
- P1 (source pitfall) — A description too vague to match: By far the most common reason a memory is never surfaced. Rewrite it with the words someone would actually search for.
- P2 (source pitfall) — Recording a project-specific fact in the user layer: It then follows you between projects and is invisible to the team it was about. Check `phronix_status()` before writing.
- P3 (source pitfall) — Writing a memory with no links: Nothing pulls it in indirectly, so it surfaces only on a direct lexical hit — which means it is found when you already knew to look for it, and not otherwise.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_memory_plan`, validator `phronix_memory_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `slug_name` failed: use a stable lowercase slug name (R2); the same name updates the memory
- `type_allowed` failed: type is project, feedback, reference or lesson; type: user is rejected (R3, phronix-privacy R2)
- `description_specific` failed: rewrite the description as a specific sentence with the words someone would search, not a label (I3, P1)
- `no_relative_dates` failed: convert relative dates to absolute YYYY-MM-DD (I3)
- `body_present` failed: write the fact itself in body
- `feedback_has_why` failed: a feedback memory needs a 'Why:' line (R1)
- `feedback_has_how` failed: a feedback memory needs a 'How to apply:' line (I2)
- `lesson_has_symptom` failed: a lesson memory is symptom -> root cause -> exact fix, the symptom as it actually appears (I2)
- `linked` failed: add at least one [[wikilink]] to a related memory or capability (I4, P3)
- `layer_known` failed: name the write layer: project (repo), user (you only) or bundled (R4, P2)
- `no_identifying_detail` failed: memory is committed and shared: replace user paths and emails with placeholders ($HOME, <user>) (R3)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A memory is never surfaced: rewrite its description with the words someone would search and add links (P1, P3), then search again.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A fact that turned out to be a procedure moves to a capability; a dated incident about one subject moves to that capability's LESSONS.md (X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Specific description + type-specific must-include part + [[links]] + the right layer is what makes a memory surface (phronix-memory I2-I4, 2026-09-15).
- `phronix_memory_plan` -> follow the checklist -> `phronix_memory_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
