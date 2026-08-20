---
name: phronix-memory
description: What belongs in memory versus a skill, the four memory types and when to use each, writing descriptions that retrieve, wikilinks, and how memory reaches the model automatically. Load before recording a durable fact or wondering why a memory was never surfaced.
subject: the durable memory store of facts, decisions and guidance
type: skill
---

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

## References

### X1 — Where lessons about a subject go instead

A pitfall or dated incident about a specific subject belongs in that skill's
LESSONS.md, not the memory store: [[phronix-skill-authoring#R4]].

### X2 — How memory is retrieved

[[phronix-context-economy#I1]].
