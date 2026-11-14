---
name: phronix_context_economy
description: Locate, don't read: open every task with both retrieval tools (skills = how to do it, memory = what went wrong before), read index matches before blocks, follow [[links]], use the knowledge graph for code (file:line, explain, affected), reformulate rather than widen. Load before orienting in an unfamiliar tree or skill, before grepping a tree to find something, before editing a shared symbol, or when a graph line number does not match the file (stale graph).
---
Cross-references: [[knowledge]], [[lessons]], [[phronix_memory]], [[phronix_skill_authoring]]

# Context economy: locate, don't read

Converted from the dftracer-agents skill `phronix-context-economy` (subject: retrieving context without loading whole documents). Source description: Locate, don't read: the two retrieval tools for skills and memory, index-first search, the knowledge graph for code, freshness, and the limits. Load before any task that involves orienting yourself in an unfamiliar tree or skill.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** Duplicates knowledge's Rules (knowledge_search first, read graph rows then knowledge_read only the sections needed, follow [[links]], reformulate rather than widen) and lessons (lesson_search before acting). In the store context_skills/context_memory map to knowledge_search/lesson_search and graph_query to the graph rows; candidate to merge into knowledge.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Open every task with both retrieval tools |
| `I2` | Instructions | Read the index matches before the blocks |
| `I3` | Instructions | Follow the references you are given |
| `I4` | Instructions | Use the graph for code |
| `I5` | Instructions | Reformulate rather than widen |
| `R1` | Rules | Never load a whole skill |
| `R2` | Rules | Locate before you read |
| `R3` | Rules | Run `affected` before editing anything shared |
| `R4` | Rules | Trust the graph over your recollection of the tree |
| `R5` | Rules | Reading the whole file is sometimes right |
| `X1` | References | Why skills are shaped for partial loading |
| `X2` | References | What the two stores hold |

## Instructions

### I1 — Open every task with both retrieval tools

```
context_skills(task="<what you are about to do>")   # HOW TO DO IT
context_memory(topic="<the subject>")               # WHAT WENT WRONG BEFORE
context_for_task(task="<...>")                      # both, in one call
```

They answer different questions and are separate tools for that reason. Searched
together, the stronger lexical match wins regardless of which you asked, and you
proceed with half of what you needed.

### I2 — Read the index matches before the blocks

`context_skills` returns `index_matches` — the catalogue rows that matched — as
well as the blocks. The rows are a map of the subject and cost almost nothing.
Read them first; they often show that the block you want is one you did not ask
for.

### I3 — Follow the references you are given

A block may cite `[[other-skill#R2]]`. Each skill covers one subject, so anything
it needs from another is a link rather than a copy. The link is not optional
reading — it is where the rest of the answer lives.

### I4 — Use the graph for code

```
graph_query(scope="project", question="<what you are looking for>")  # -> file:line
graph_query(mode="explain",  symbol="<symbol>")                      # callers/callees
graph_query(mode="affected", symbol="<symbol>", depth=2)             # blast radius
```

Open only the files it names.

### I5 — Reformulate rather than widen

If a search returns little, try different phrasing — the subject's vocabulary is
rarely the asker's. If a graph BFS returns generic nodes, ignore them; widening the
question makes it worse.

## Rules

### R1 — Never load a whole skill

The retrieval tools return the exact labelled blocks. A whole skill costs what a
whole source file costs, and the cost is not just tokens: everything loaded stays
in context for the rest of the session, crowding out the work. Load a whole file
only when you genuinely need every part of it — an exhaustive checklist walk.

### R2 — Locate before you read

Do not grep or Read a tree to find where something lives. Ask the graph, then open
only the `file:line` it names. Locating costs a few hundred tokens; reading the
files it names costs tens of thousands.

### R3 — Run `affected` before editing anything shared

State the blast radius. A "local" fix that silently breaks a caller is the exact
failure this prevents.

### R4 — Trust the graph over your recollection of the tree

It is rebuilt from the files; your memory is from three steps ago. If a returned
line number does not match the file, that is a stale graph —
`graph_ensure(force=True)`, not a manual search.

### R5 — Reading the whole file is sometimes right

The discipline is "locate before you read", not "never read". Read it all when the
file is small, when you need an exhaustive walk, when you are about to rewrite it,
or when the graph returned nothing after two reformulations.

### Using the tools (capability)

- Render the procedure with `phronix_context_economy_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `task`, `skills_query`, `memory_query`, `index_matches_read`, `files_read`, `located_by_graph`, `edits_shared`, `blast_radius`, `whole_skill_loaded`, `whole_load_reason`) to `phronix_context_economy_check`; a step is done only when the check passes.

## References

### X1 — Why skills are shaped for partial loading

The schema exists to make block-level retrieval possible:
[[phronix-skill-authoring#R1]].

### X2 — What the two stores hold

Skills hold instructions and rules; memory holds pitfalls, lessons and durable
facts: [[phronix-memory#R1]].

## Constraints

- Do not grep or Read a tree to find where something lives; ask the graph first (R2).
- Everything loaded stays in context for the rest of the session: load blocks, not whole skills (R1).

## Corner cases

- Searched together, the stronger lexical match wins regardless of which store you asked, so skills and memory are separate tools (I1).
- Widening a question that returned generic graph nodes makes it worse; reformulate instead (I5).
- P1 (source pitfall) — Searching skills and memory with one query and stopping there: You get whichever store happened to match more strongly and never learn that the other had the answer. Always call both.
- P2 (source pitfall) — Loading a whole skill because the pointer looked inconvenient: This is the failure the tools are designed around: handed a `file:line`, an agent often loads the file anyway. The retrieval tools return the section text directly so there is no reason to.
- P3 (source pitfall) — Treating a stale graph as a missing answer: A line number that does not match the file means the graph is behind, not that the symbol moved. Force a rebuild before concluding anything.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_context_economy_plan`, validator `phronix_context_economy_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `task_named` failed: name the task the context was gathered for
- `skills_searched` failed: search skills (context_skills / knowledge_search): how to do it (I1)
- `memory_searched` failed: also search memory (context_memory / lesson_search): what went wrong before; one query finds only the stronger store (I1, P1)
- `index_first` failed: read the index matches before the blocks (I2)
- `located_first` failed: locate with graph_query before reading files; open only the file:line it names (R2)
- `blast_radius` failed: run graph_query(mode=affected) and state the blast radius before editing (R3)
- `whole_load_justified` failed: do not load a whole skill; retrieve the labelled blocks (R1); whole loads only for the R5 reasons
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- Graph answers look wrong: rebuild it (graph_ensure(force=True)) before concluding anything (R4, P3).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A search that missed what existed: fix the heading or description that should have matched (knowledge's Self-learn).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- context_skills + context_memory, index matches first, graph_query for file:line, affected before shared edits (phronix-context-economy I1-I5, 2026-09-15).
- `phronix_context_economy_plan` -> follow the checklist -> `phronix_context_economy_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
