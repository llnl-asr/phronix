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
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R0b` | Rules | Every label you cite must resolve |
| `R0c` | Rules | Be specific to THIS task, and name every way it can go wrong |
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

### R0 — A skill that solves a problem must say how to solve it

**Applies to every writer of skills** — research, exploring, build-solution, the
learner, and both reconciliation passes. Whatever else a skill records, if it
claims to cover a problem then its `## Instructions` must contain the steps that
fix it: the file, the function, the line, and what to change it to, in order.

Three things this rules out, all of them observed:

* **An empty `## Instructions` section.** Rules and References are the
  supporting material; instructions are the skill. A file with none is notes.
* **Instructions that live in a reference.** If the reader must follow a link to
  learn what to DO, put it inline. References are for why, not how.
* **Adjudication in place of method.** "R2 is stale", "this finding supersedes
  that one" is bookkeeping between passes. Reconcile as much as you like — then
  write down what the surviving answer tells the next agent to do.

Measured on `pallets__flask-4045`. The skill written for it was 7,433 characters
and its `## Instructions` section was EMPTY — every word Rules and References,
arguing about which earlier finding superseded which:

```
sections present:  R1 R2 X1 X2 X3 X4 X5
Instructions:      0 characters
cited I-labels:    I1, I4      defined: none
```

R1 read "R2 is stale — the second target test's cause is now known" and referred
to "I1's fix" six times. There was no I1. The correct answer was in the file —
raise `ValueError` in `Blueprint.__init__`, and for `endpoint` and
`view_func.__name__` in `add_url_rule` — buried in commentary about which prior
claim had been retired.

What it cost: the model handed this skill scored **0/2** target tests. The same
task solved from scratch, with no skill at all, scored **1/2** on its first
attempt and 2/2 by its third. Reuse was worse than nothing, because the one
thing a weaker model needs — the steps — was the one thing absent.

Read your own skill back before you finish and ask: **could I fix this from the
Instructions alone?** If not, the next agent does the work again, or does it
worse than if you had written nothing.

### R0b — Every label you cite must resolve

A bare label — `I1`, `X15` — means "a section of THIS skill". Write one that
does not exist and the reader follows a pointer to nothing.

Two legal forms, and nothing else:

* `X1` — a section in this skill. It must be present in this file.
* `[[other-skill#X1]]` — a section of another skill, named in full.

Never cite an identifier that lives somewhere other than a skill. Research
records name their approaches internally, and those names are not section
labels: writing "the winning approach (X11/X15, all-three-valueerror-complete-
upstream)" puts a research-record identifier where a reader expects a section,
and following it finds nothing. Say what you mean instead — "the complete fix,
all three checks converted" — and link the skill section that holds it.

Measured twice on `pallets__flask-4045`. First an empty-instructions skill cited
"I1's fix" six times with no I1 in the file. Then, after that was fixed, a new
skill still carried `X10`, `X11`, `X14`, `X15` — approach identifiers from the
research record, in a skill whose own sections are `I1`, `I2`, `X1`.

### R0c — Be specific to THIS task, and name every way it can go wrong

A solution skill is read by whoever picks the task up next, and that is usually
a smaller model than the one that solved it. Write for that reader.

**Specific, never general.** "Validate the input" is advice. "In
`src/flask/blueprints.py`, in `Blueprint.__init__`, immediately before
`self.name = name`, insert `if "." in name: raise ValueError(...)`" is a skill.
If a sentence would still be true of a different bug in a different project, it
is not earning its place — delete it or replace it with the specific form.

Name the exact file, the exact function, the exact line it goes before or after,
the exact code, and the exact message string. A reader should never have to
decide anything you already decided.

**Then name every way it can still go wrong.** Correct instructions are not
enough while the obvious wrong reading is available. For each step ask: what
will someone plausibly write instead, and why? Put that in the skill with the
reason it fails. At minimum, whenever they apply:

* **The wrong construct with the right words.** State the exception type, the
  return value, the operator — and say the test checks it.
* **Matching the surrounding style.** If the code nearby does it the old way, a
  reader will copy its neighbours. Say so: "the existing `assert`s here are
  exactly what must change; do not follow them."
* **The incomplete subset.** If the fix needs three sites, say that one or two
  scores strictly worse than nothing, and name each site.
* **The expected collateral.** If a correct fix breaks an existing test, say
  which and why, or the reader will treat their own correct work as a mistake.

Measured on `pallets__flask-4045`. A skill carrying the complete, correct fix —
including the literal code `raise ValueError("'name' may not contain a dot '.'
character.")` — was handed to Haiku 4.5. It found all three sites, reproduced
the message string verbatim, and wrote:

```python
assert "." not in name, "'name' may not contain a dot '.' character."
```

`assert`, not `raise ValueError`. It had plainly read the block, then followed
the style of the `assert`s already beside it. The tests check for `ValueError`,
so all three edits failed: 0/2 — the right change, in the right places, in the
wrong construct.

Nothing in the skill said "it must be `ValueError`, and the surrounding
`assert`s are the trap." The model that wrote the skill did not need telling.
The model that read it did.

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
