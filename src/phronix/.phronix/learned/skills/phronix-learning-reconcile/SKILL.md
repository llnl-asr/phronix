---
name: phronix-learning-reconcile
description: The slow tier of the always-on learner, run every minute: keep exactly one copy of each fact with everything else referencing it, retire what has been falsified, and improve how the learner itself learns.
subject: phronix-learning-reconcile
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Find the neighbourhood before judging it |
| `I2` | Instructions | Merge duplicates into one block, by label |
| `I3` | Instructions | Reference instead of restating |
| `I4` | Instructions | Retire what has been falsified |
| `I5` | Instructions | Improve the learner's own skills |
| `I6` | Instructions | Merge sibling subjects into one topic |
| `I7` | Instructions | Shape a topic skill: the answer, then the cases |
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R1` | Rules | Merging is lossy; keep the sharper wording |
| `R2` | Rules | Never rewrite what a stage is reading |
| `R3` | Rules | A skill that is only reorganised was not reconciled |
| `R4` | Rules | skill_write_lesson appends by label, it never updates an existing title in place |
| `R5` | Rules | Four-plus consecutive null-result cycles on the same facts is a stopping signal |
| `R6` | Rules | skill_define and skill_write_lesson can land in a layer this project's skill_load never reads |
| `X1` | References | Why one copy, and what a copy costs |

## Instructions

### I1 — Find the neighbourhood before judging it

Work one subject at a time. `graph_query` for the subject, then `graph_get_node` on the ids it returns, and read the whole set before changing any of it.

The graph is what makes reconciliation possible: it links a lesson to the skills, observations and tools that touch it, so "everything already written about parsing subprocess output" is a lookup rather than a recollection. Two blocks that say the same thing in different words are invisible to a keyword search and obvious in the graph.

### I2 — Merge duplicates into one block, by label

Where two blocks state the same fact, keep one and delete the other. Keep the block whose label is already referenced elsewhere — references are the expensive thing to fix — and fold in whatever the other said better.

Update **by label** (`L3`, `I2`). The labels are stable and never recycled, so a reference written last week still resolves after your merge.

### I3 — Reference instead of restating

Where a block *depends* on another rather than repeating it, link it by label rather than restating the dependency. A reference stays right when the other block changes; a restatement silently stops matching, and the two then disagree with no way to tell which is current.

This is most of the job. Reconciling is not mainly about adding — it is about there being one true copy of each fact and one place to correct it.

### I4 — Retire what has been falsified

`research_notice` also shows what stopped working. A lesson contradicted by later observations is worse than no lesson: it is confidently wrong knowledge that every retrieval propagates.

Delete it, or rewrite it with the condition that turned out to matter. Say which observations falsified it.

**A failed attempt does not falsify the approach it was attempting.** These are different claims and only one of them was tested:

- *the implementation failed* — the code that was written did not do what was intended. This is what a failing test shows.
- *the approach is wrong* — no implementation of this idea could work. A single attempt cannot show this, and almost never does.

Measured, and this is why the rule exists: `pallets__flask-4045` researched three angles and found the right one — validate the blueprint name, raise where endpoint names are already validated. The attempt implemented it and the check did not fire, so the reconciler wrote *"dot validation attempt falsified … should no longer be considered a valid approach"* and retired the lesson that would have told the next task to use it. Dot validation is the accepted fix. The store now rules out the correct answer, durably, and nothing downstream can tell.

Before retiring a lesson because an attempt failed, ask what was actually shown. If the answer is "this code did not work", rewrite the lesson with that detail — "validation added to `Blueprint.__init__` did not fire for the construction path the test uses" is true, specific and useful. **Retire the approach only when the evidence rules out the idea itself**, not the attempt at it.

When you cannot tell which it was, keep the lesson and record the doubt. An idea wrongly kept costs one attempt; an idea wrongly retired costs every future task that would have used it.

### I5 — Improve the learner's own skills

The learner is subject to its own method. Every cycle — capture and reconcile alike — reports what it did through `research_observe(topic="learning")`, so the learner's own behaviour arrives in the same stream as everything else.

Read those. When a way of learning repeatedly fails or repeatedly works, write it into `phronix-learning-capture` or this skill as a block, exactly as you would for any other subject:

- A kind of finding that keeps producing blocks nobody retrieves is a lesson about what not to capture.
- A merge rule you keep applying by hand is a lesson that belongs in `I2`.
- A phrasing that makes blocks findable in the graph is worth stating once, here.

Under the same constraint as everything else: only what repeated, and only where it will be found. A learner that rewrites its own method every cycle is not improving, it is drifting — the bar is a pattern across cycles, not a single awkward one.

### I6 — Merge sibling subjects into one topic

`I1` works one subject at a time, so duplication *between* subjects is invisible to it — and that is where duplication actually accumulates. One Flask issue produced `column-domain`, `column-domain-rule`, `column-domain-files`, `cases-column-domain` and `based-column-domain`; one sympy issue produced six. Each was internally consistent, so nothing per-subject ever flagged them.

So before working a subject, `graph_query` its *neighbours* and read their descriptions. Where several name the same repository, file and defect, they are one topic:

- keep the name a later task would search for — the topic (`sympy-itermonomials`, `flask-cli-routes-domain`), not the fragment of a question that happened to be asked first;
- fold the siblings' blocks in under `I2`, by label;
- leave each old name in place as a pointer skill — a description saying "superseded, merged into" and a link to the topic skill, and nothing else. Retrieval by the old name still lands somewhere true, and existing references keep resolving.

A raced task's `solution-<subject>-<plan>` candidates are **not** siblings to merge. They are already linked from `solution-<subject>` by design, and each records an idea with the check that settled it. Merge across subjects; leave the candidates under theirs.

### I7 — Shape a topic skill: the answer, then the cases

A topic skill is found the way a tool is found: someone describes a problem and wants the one thing that handles it. So its `description` names the topic in the words a later task will use — the repository, the file, the defect — and its body opens with the answer, not with the history of how it was reached.

Under that, one **case** per instance the topic has actually seen. A case is three things, and it is worthless without the third:

| what | example |
| --- | --- |
| the situation | `min_degrees` given as an int, mixed monomials missing |
| what worked, with what | `sum(powers.values())` in both loops of `itermonomials` |
| what settled it | the target test that went from fail to pass |

Record what did **not** work in the same table, one line, with the check that killed it. That is the half a reader cannot reconstruct and the half that saves the next task an attempt.

Keep a case inline while it is a few lines. When one grows past that — a long trace, a full diff, a sequence of commands — move it to its own skill and leave a one-line row linking it with `[[name]]`. The split is about what the entry point can stay readable at, not about importance: the topic skill is read on every retrieval for this area, and a case is read only when someone is on that case. `R2` in `phronix-solution-candidate` is the same economics one level down.

Do not let the topic become a log. Cases that turned out to be the same case are one case with two instances named; that merge is `I2`, applied to cases.

## Rules

### R0 — A skill that solves a problem must say how to solve it

[[phronix-skill-authoring]] `R0` is the rule and carries the evidence. In short: whatever else you record, the `## Instructions` must contain the steps that fix the problem — file, function, line, and what to change it to. Not a description of the bug, not an argument about which finding is current.

Measured: a skill written for `pallets__flask-4045` held the complete correct answer inside 7,433 characters of Rules and References with an EMPTY Instructions section, and cited an `I1` that did not exist. The model handed it scored 0/2; the same task from scratch scored 1/2 on its first try. Reuse was worse than nothing.

Read it back before you finish: could someone fix this from the Instructions alone?

### R1 — Merging is lossy; keep the sharper wording

When you fold two blocks together, the result must say everything the more specific of the two said. The common failure is a merge that keeps the general sentence and drops the condition — leaving a block that is true in fewer cases than it now claims.

If the two cannot be merged without losing a condition, they are not duplicates. Leave both and link them.

### R2 — Never rewrite what a stage is reading

Research and attempts run while you do. Change one block at a time, through the skill tools, and never hold a file open across a long deliberation.

A minute is a budget, not a target. An unfinished reconciliation costs nothing — the duplicates are still there next cycle — and a stalled pass costs the run.

### R3 — A skill that is only reorganised was not reconciled

Rewriting headings, resorting an index and re-wording blocks produces a diff and no change in what any future task retrieves. It also invalidates nothing and helps nobody.

Report merges, references added, and retirements. If a cycle found no duplicates and nothing falsified, that is the correct outcome and the right thing to report.

### R4 — skill_write_lesson appends by label, it never updates an existing title in place

Calling `skill_write_lesson` again against the same skill with an unchanged title does NOT update the existing lesson in place — it appends a new lesson with the identical title, an immediate duplicate that then has to be re-merged next cycle. The "label stable if title unchanged" guarantee (I2/R1 in this skill) applies to `skill_define`, not to `skill_write_lesson`. To widen or correct an existing lesson found during reconcile, read the current LESSONS.md, then use `skill_define` with the full lessons array and the same explicit label to update it in place. See `P1` in this skill's LESSONS.md for the incident that surfaced this.

### R5 — Four-plus consecutive null-result cycles on the same facts is a stopping signal

If a reconcile cycle's re-verification of a fact (e.g. pallets-flask-4045's dot-validation finding, or phronix-self-healing's rebuild-race lesson) comes back "already correctly captured, nothing to merge or retire" for the fourth or later consecutive cycle, stop re-verifying that fact every cycle. Confirming the same unchanged content repeatedly spends a cycle's budget without producing anything a future task can retrieve — `research_notice` already surfaces the repeat count, so this is arithmetic, not a judgement that needs redoing each time.

How to apply: when `research_notice` shows 3+ prior "correct null result" reports against the same skill/labels, skip re-checking those specific blocks this cycle unless a new report explicitly claims something changed about them; spend the cycle on facts that haven't been checked yet instead. Do not write yet another "still consistent, nothing to merge" observation for the same fact — that report is itself what causes the repeat.

This rule previously existed only in a copy of this skill under a layer that `skill_load`/`graph_query` do not surface by default for this project, which is why cycles kept repeating past the fourth despite it being written down once already — see the layer rule below.

### R6 — skill_define and skill_write_lesson can land in a layer this project's skill_load never reads

Both tools accept a `layer` override, and calls made without pinning one can resolve to a store outside this project's own `store/.phronix/skills/` tree (e.g. a shared `/usr/.../phronix/.phronix/learned/skills/` path). `graph_query`/`graph_get_node` see every layer and will report a block as present; `skill_load` on this project by default does not, so a rule written there is invisible to the very cycles that need it — exactly what happened to the two rules above, silently causing the "4+ null cycles" problem they warn against.

How to apply: when reconciling, if `graph_query`/`graph_get_node` surfaces a block under this skill's name at a `source_file` outside `store/.phronix/skills/phronix-learning-reconcile/`, treat it as stranded — re-write it into the project layer via `skill_define` (which resolves to `store/.phronix/skills/...` for this project by default) so `skill_load` picks it up. Prefer checking `source_file` on any surprising `graph_get_node` result before trusting that a rule is actually reachable.

## References

### X1 — Why one copy, and what a copy costs

Two blocks saying nearly the same thing are worse than either alone. A future retrieval gets both, cannot tell which is current, and a correction applied to one leaves the other confidently wrong — so the library degrades exactly where it was most used.

The single-copy rule is what makes the library correctable at all: one statement of a fact, one place to fix it, and every other mention a reference that follows the fix automatically.
