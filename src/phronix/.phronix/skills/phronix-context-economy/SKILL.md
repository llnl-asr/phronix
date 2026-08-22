---
name: phronix-context-economy
description: Locate, don't read: the two retrieval tools for skills and memory, index-first search, the knowledge graph for code, freshness, and the limits. Load before any task that involves orienting yourself in an unfamiliar tree or skill.
subject: retrieving context without loading whole documents
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

## References

### X1 — Why skills are shaped for partial loading

The schema exists to make block-level retrieval possible:
[[phronix-skill-authoring#R1]].

### X2 — What the two stores hold

Skills hold instructions and rules; memory holds pitfalls, lessons and durable
facts: [[phronix-memory#R1]].
