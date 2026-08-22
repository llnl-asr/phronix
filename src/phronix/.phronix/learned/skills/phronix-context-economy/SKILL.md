---
name: phronix-context-economy
description: Locate, don't read: the two retrieval tools for skills and memory, index-first search, the knowledge graph for code, freshness, and the limits. Load before any task that involves orienting yourself in an unfamiliar tree or skill.
subject: phronix-context-economy
type: skill
---

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
| `R6` | Rules | When graph rebuild throws FileNotFoundError, stop retrying and fall back |
| `R7` | Rules | A worktree can lag the main checkout's fixes |
| `X1` | References | Why skills are shaped for partial loading |
| `X2` | References | What the two stores hold |
| `X3` | References | Reconcile tracker: graph-rebuild-FileNotFoundError (mcp-server stage) |

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

### R6 — When graph rebuild throws FileNotFoundError, stop retrying and fall back

`graph_ensure(force=True)` (and any `graph_query`/`graph_get_node` call that triggers a rebuild) has failed with `FileNotFoundError` repeatedly and consistently (running count tracked in [[phronix-context-economy#X3]]), across many unrelated topics and both `graph_query` and `graph_get_node` paths, all from the `mcp-server` stage specifically — this is a broken `mcp-server` install or missing rebuild input, not staleness. A second symptom of the same broken install has also been observed directly: `graph_get_node` failing with `graphify produced no graph` / `Directory not empty: .../learner-cache/graph/.../skills'` on a leftover staged directory. [[phronix-context-economy#R4]] ("force a rebuild") does not apply once a rebuild has already thrown either error in this session — retrying it repeats the same failure.

By contrast, rebuilds triggered from non-mcp-server call sites (e.g. this skill's own reconcile-pass `graph_query`/`graph_get_node` calls) have rebuilt cleanly on every reconcile cycle so far, with no FileNotFoundError. This does not weaken the guidance below — it sharpens it: the failure is scoped to how the `mcp-server` stage specifically invokes rebuild (e.g. concurrent/staged-directory state during a task run), not a permanently broken install, so still stop retrying whenever the error is actually seen, which so far has only been from that stage.

**How to apply:** on the first `FileNotFoundError` (or the `graphify produced no graph` / `Directory not empty` variant) from a graph rebuild, do not retry the same call. Fall back to `skill_search` (index-first, no graph dependency) for docs/skills, and to `grep`/`Read` directly for code in this session. Report the error once; do not re-attempt graph rebuild speculatively later in the same run. Track the running count and any change in failure shape or hypothesis in [[phronix-context-economy#X3]] rather than adding a new reference block each cycle.

### R7 — A worktree can lag the main checkout's fixes

A git worktree branched off a base commit does not automatically pick up fixes/commits that exist in the main checkout of the same repo (they were applied there after the worktree was branched, or on a different ref). Before concluding a bug reproduces or a fix is missing inside a worktree, diff its state against the main checkout — a "missing fix" may just be a stale worktree, not a real gap.

## References

### X1 — Why skills are shaped for partial loading

The schema exists to make block-level retrieval possible:
[[phronix-skill-authoring#R1]].

### X2 — What the two stores hold

Skills hold instructions and rules; memory holds pitfalls, lessons and durable
facts: [[phronix-memory#R1]].

### X3 — Reconcile tracker: graph-rebuild-FileNotFoundError (mcp-server stage)

[[phronix-context-economy#R6]] fact: 25/25 FileNotFoundError (or Directory-not-empty) failures on record, all from the `mcp-server` stage, across at least 6 named topics (pallets__flask-4045, pallets__flask-5063, pylint-dev__pylint-5859, pylint-dev__pylint-7080, sympy__sympy-21847, sympy__sympy-24066) plus two additional unnamed-task occurrences reported across cycles (one this cycle). Still 0/25 worked; still flagged "repeated." Multiple consecutive reconcile cycles have now seen this reconcile pass's own `graph_query`/`graph_get_node` calls (a call site outside mcp-server) rebuild cleanly with no FileNotFoundError — this strengthens rather than falsifies the hypothesis that the break is scoped to how the `mcp-server` stage specifically invokes rebuild (e.g. concurrent/staged-directory state during a task run), not a broken install generally. Does not weaken R6's "stop retrying and fall back" guidance — keep applying it whenever the error is actually seen from that stage.

This block is the single tracker for this fact and its label (X3) is kept stable across updates — do NOT change this title (it must not embed the count, or the label gets reallocated and existing [[...#X3]] references break). Per [[phronix-learning-reconcile#R4]]: widen this block's count/hypothesis in place on later cycles by editing the body only; do not add a new X-block unless the tracked hypothesis itself changes (new stage affected, new failure shape, or worked-count no longer 0/N).
