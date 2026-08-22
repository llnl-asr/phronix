---
name: phronix-skill-authoring
description: The skill file schema: one subject per skill, labelled blocks as stable keys, the Index as catalogue, references as foreign keys, association skills as join tables, and lessons kept in a separate file. Load before creating a skill or restructuring an existing one.
subject: authoring and growing skill files
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Decide whether this is a new subject |
| `I2` | Instructions | Write the description as the retrieval signal |
| `I3` | Instructions | Add blocks, one idea each |
| `I4` | Instructions | Link instead of restating |
| `I5` | Instructions | Create an association skill for a genuine pair |
| `I6` | Instructions | Split a skill that has outgrown its subject |
| `R1` | Rules | One skill covers exactly one subject |
| `R2` | Rules | Labels are stable keys and are never reused |
| `R3` | Rules | The Index is generated, never hand-edited |
| `R4` | Rules | Pitfalls and lessons never go in SKILL.md |
| `R5` | Rules | A block states the rule before the rationale |
| `R6` | Rules | Never edit a skill file by hand |
| `R7` | Rules | A higher layer replaces a skill wholesale |
| `X1` | References | Deciding code versus prose |
| `X2` | References | Proving the skill's claims |
| `X3` | References | What must never appear in a skill |

## Instructions

### I1 — Decide whether this is a new subject

Ask: does an existing skill's `subject:` already cover this? If yes, add a block
there. If no, create one — `skill_create(name=..., description=..., subject=...)`.

Do NOT widen an existing skill to fit. A skill covering two subjects becomes
findable for neither, because index-first retrieval matches on the subject.

### I2 — Write the description as the retrieval signal

One or two sentences: what this subject is, and when to load it. Include the words
someone would actually search for — the tool name, the error phrase, the task verb.

"Notes about the build" ranks for nothing. "Building and linking the service
against system OpenSSL, including the version pinning it requires" ranks for
several real queries.

### I3 — Add blocks, one idea each

```
skill_write(skill=..., kind="instruction", title=..., body=...)   # I* — how, in order
skill_write(skill=..., kind="rule",        title=..., body=...)   # R* — constraints
skill_write(skill=..., kind="reference",   title=..., body=...)   # X* — links out
```

The label is allocated for you and the Index is regenerated. Never hand-write
either.

### I4 — Link instead of restating

When a block needs something from another subject, cite it: `[[other-skill#R2]]`.
Copying the content duplicates a fact that will then be updated in one place and
not the other — the classic denormalisation bug, with the same consequence.

### I5 — Create an association skill for a genuine pair

When two subjects interact in ways neither owns alone — a specific library on a
specific platform, say — create a join:

```
skill_create(name="x-on-y", kind="association", subjects="x, y", ...)
```

It holds only the references between their blocks and the rules true of the
*combination*. No instructions of its own: those belong to the subjects it joins.

### I6 — Split a skill that has outgrown its subject

Symptoms: agents load it and use one block; the description no longer describes
it; blocks contradict each other. In order of preference:

1. **Extract a capability** — a large skill usually has a deterministic core that
   should be code.
2. **Split by subject** and link the parts.
3. **Externalize reference material** into sibling files, loaded on demand with
   `skill_load(name=..., file=...)`.

## Rules

### R1 — One skill covers exactly one subject

This is the schema's central constraint and everything else follows from it.
Retrieval is index-first: it identifies the *subject* before it looks at content.
A skill spanning two subjects has an index describing neither, and is reached by
accident or not at all.

### R2 — Labels are stable keys and are never reused

`R3` means the same block forever. Deleting a block does not free its number,
because a recycled label silently redirects every existing `[[skill#R3]]`
reference to different content — the one failure stable keys exist to prevent.

### R3 — The Index is generated, never hand-edited

It is the catalogue retrieval reads first. An index that drifts from the content
routes agents to blocks that no longer say what it claims — worse than no index,
because it is trusted. `skill_write` regenerates it on every write.

### R4 — Pitfalls and lessons never go in SKILL.md

They live in `LESSONS.md` and are retrieved by `context_memory`, not
`context_skills`. "How do I do this" and "what went wrong last time" are different
questions; merging them means every retrieval of either drags in the other, and
the file grows until nobody can load part of it.

### R5 — A block states the rule before the rationale

The rule is what gets acted on; the reasoning is what gets read when someone wants
to change it. Reversing the order buries the actionable part.

### R6 — Never edit a skill file by hand

Use `skill_write` / `skill_write_lesson`. Editing directly bypasses redaction,
skips label allocation, leaves the Index stale, and does not mark the graph dirty
— so the content will not be findable until the next hash sweep.

### R7 — A higher layer replaces a skill wholesale

Same name in a higher layer shadows the lower one entirely — no field-level merge.
Wholesale override is deliberate: a half-overridden document is far harder to
reason about than a replaced one. Writing to a shadowed skill forks the whole file
first, so the copy is a superset.

## References

### X1 — Deciding code versus prose

If the procedure is deterministic it is not a skill at all:
[[phronix-capability-authoring#R1]].

### X2 — Proving the skill's claims

Every subject should have a corrector: [[phronix-verification#R1]]. The built-in
structural corrector already enforces this schema.

### X3 — What must never appear in a skill

Skills are committed and shared: [[phronix-privacy#R1]].
