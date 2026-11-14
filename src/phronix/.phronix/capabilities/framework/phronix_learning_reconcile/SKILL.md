---
name: phronix_learning_reconcile
description: The slow tier (every minute) of the always-on learner: per subject find the graph neighbourhood, merge sibling subjects into one topic skill (old names left as pointer skills), shape topic skills as answer then cases (situation, what worked, what settled it), merge duplicate blocks by label keeping both specifics, reference instead of restating, retire only what evidence falsified (a failed attempt does not falsify the approach), and improve the learner's own skills from repeated patterns. Load when consolidating lessons or skills, when one issue produced several near-identical skills, or before retiring a lesson because an attempt failed.
---
Cross-references: [[lessons]], [[knowledge]], [[capability_builder]], [[phronix_learning_capture]], [[phronix_skill_authoring]], [[phronix_solution_candidate]]

# Learning reconcile: the slow tier of the always-on learner

Converted from the dftracer-agents skill `phronix-learning-reconcile` (subject: reconciling learned skills into one true copy, and improving the learner). Source description: The slow tier of the always-on learner, run every minute: keep exactly one copy of each fact with everything else referencing it, retire what has been falsified, and improve how the learner itself learns.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** Largely duplicates the store's lessons consolidation (consolidation_report, read every member with lesson_get, lesson_merge into the single best home keeping every fact, consolidation_ask on contradictions, consolidation_keep with why, overlapping capabilities -> capability_update the better home). Phronix-specific parts: sibling-subject topic merge with pointer skills, the topic-skill case table, and 'a failed attempt does not falsify the approach'. Strong candidate to merge into lessons.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Find the neighbourhood before judging it |
| `I1b` | Instructions | Merge sibling subjects into one topic |
| `I1c` | Instructions | Shape a topic skill: the answer, then the cases |
| `I2` | Instructions | Merge duplicates into one block, by label |
| `I3` | Instructions | Reference instead of restating |
| `I4` | Instructions | Retire what has been falsified |
| `I5` | Instructions | Improve the learner's own skills |
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R0c` | Rules | Merging must not make a solution skill more general |
| `R1` | Rules | Merging is lossy; keep the sharper wording |
| `R2` | Rules | Never rewrite what a stage is reading |
| `R3` | Rules | A skill that is only reorganised was not reconciled |
| `X1` | References | Why one copy, and what a copy costs |

## Instructions

### I1 — Find the neighbourhood before judging it

Work one subject at a time. `graph_query` for the subject, then `graph_get_node` on the ids it returns, and read the whole set before changing any of it.

The graph is what makes reconciliation possible: it links a lesson to the skills, observations and tools that touch it, so "everything already written about parsing subprocess output" is a lookup rather than a recollection. Two blocks that say the same thing in different words are invisible to a keyword search and obvious in the graph.

### I1b — Merge sibling subjects into one topic

`I1` works one subject at a time, so duplication *between* subjects is invisible
to it — and that is where duplication actually accumulates. One Flask issue
produced `column-domain`, `column-domain-rule`, `column-domain-files`,
`cases-column-domain` and `based-column-domain`; one sympy issue produced six.
Each was internally consistent, so nothing per-subject ever flagged them.

So before working a subject, `graph_query` its *neighbours* and read their
descriptions. Where several name the same repository, file and defect, they are
one topic:

- keep the name a later task would search for — the topic (`sympy-itermonomials`,
  `flask-cli-routes-domain`), not the fragment of a question that happened to be
  asked first;
- fold the siblings' blocks in under `I2`, by label;
- leave each old name in place as a pointer skill — a description saying
  "superseded, merged into" and a link to the topic skill, and nothing else.
  Retrieval by the old
  name still lands somewhere true, and existing references keep resolving.

A raced task's `solution-<subject>-<plan>` candidates are **not** siblings to
merge. They are already linked from `solution-<subject>` by design, and each
records an idea with the check that settled it. Merge across subjects; leave the
candidates under theirs.

### I1c — Shape a topic skill: the answer, then the cases

A topic skill is found the way a tool is found: someone describes a problem and
wants the one thing that handles it. So its `description` names the topic in the
words a later task will use — the repository, the file, the defect — and its
body opens with the answer, not with the history of how it was reached.

Under that, one **case** per instance the topic has actually seen. A case is
three things, and it is worthless without the third:

| what | example |
| --- | --- |
| the situation | `min_degrees` given as an int, mixed monomials missing |
| what worked, with what | `sum(powers.values())` in both loops of `itermonomials` |
| what settled it | the target test that went from fail to pass |

Record what did **not** work in the same table, one line, with the check that
killed it. That is the half a reader cannot reconstruct and the half that saves
the next task an attempt.

Keep a case inline while it is a few lines. When one grows past that — a long
trace, a full diff, a sequence of commands — move it to its own skill and leave
a one-line row linking it with `[[name]]`. The split is about what the entry
point can stay readable at, not about importance: the topic skill is read on
every retrieval for this area, and a case is read only when someone is on that
case. `R2` in `phronix-solution-candidate` is the same economics one level down.

Do not let the topic become a log. Cases that turned out to be the same case are
one case with two instances named; that merge is `I2`, applied to cases.

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

Before retiring a lesson because an attempt failed, ask what was actually shown. If the answer is "this code did not work", rewrite the lesson with that detail — *"validation added to `Blueprint.__init__` did not fire for the construction path the test uses"* is true, specific and useful. **Retire the approach only when the evidence rules out the idea itself**, not the attempt at it.

When you cannot tell which it was, keep the lesson and record the doubt. An idea wrongly kept costs one attempt; an idea wrongly retired costs every future task that would have used it.

### I5 — Improve the learner's own skills

The learner is subject to its own method. Every cycle — capture and reconcile alike — reports what it did through `research_observe(topic="learning")`, so the learner's own behaviour arrives in the same stream as everything else.

Read those. When a way of learning repeatedly fails or repeatedly works, write it into `phronix-learning-capture` or this skill as a block, exactly as you would for any other subject:

- A kind of finding that keeps producing blocks nobody retrieves is a lesson about what not to capture.
- A merge rule you keep applying by hand is a lesson that belongs in `I2`.
- A phrasing that makes blocks findable in the graph is worth stating once, here.

Under the same constraint as everything else: only what repeated, and only where it will be found. A learner that rewrites its own method every cycle is not improving, it is drifting — the bar is a pattern across cycles, not a single awkward one.

## Rules

### R0 — A skill that solves a problem must say how to solve it

[[phronix-skill-authoring]] `R0` is the rule and carries the evidence, and `R0b` is its companion: every label you cite must resolve — a bare `X15` means a section of THIS skill, and a research record's approach identifier is not one. In short:
whatever else you record, the `## Instructions` must contain the steps that fix
the problem — file, function, line, and what to change it to. Not a description
of the bug, not an argument about which finding is current.

Measured: a skill written for `pallets__flask-4045` held the complete correct
answer inside 7,433 characters of Rules and References with an EMPTY
Instructions section, and cited an `I1` that did not exist. The model handed it
scored 0/2; the same task from scratch scored 1/2 on its first try. Reuse was
worse than nothing.

Read it back before you finish: could someone fix this from the Instructions
alone?

### R0c — Merging must not make a solution skill more general

[[phronix-skill-authoring]] `R0c`. Reconciliation is where specificity is most
easily lost: two blocks saying nearly the same thing invite a summary, and a
summary of "raise ValueError in Blueprint.__init__ before self.name = name" and
"raise ValueError in add_url_rule for endpoint" is "validate names" — which
fixes nothing.

Merge by keeping BOTH specifics under one block, never by abstracting over them.
If the merged wording no longer names a file, a function and a line, you have
destroyed the skill while tidying it.

Carry the failures forward too. You hold what nobody downstream has: which
candidate scored what. "Converting only `Blueprint.__init__` and not the two
`add_url_rule` sites scores 1/2, not partial credit toward 2/2" is worth more
than any number of retired claims — and it is exactly what gets dropped when a
pass optimises for tidiness.

Measured: a skill carrying the literal correct code was read by a smaller model,
which reproduced its message string verbatim and still wrote `assert` where the
test wanted `raise ValueError` — 0/2.

### R1 — Merging is lossy; keep the sharper wording

When you fold two blocks together, the result must say everything the more specific of the two said. The common failure is a merge that keeps the general sentence and drops the condition — leaving a block that is true in fewer cases than it now claims.

If the two cannot be merged without losing a condition, they are not duplicates. Leave both and link them.

### R2 — Never rewrite what a stage is reading

Research and attempts run while you do. Change one block at a time, through the skill tools, and never hold a file open across a long deliberation.

A minute is a budget, not a target. An unfinished reconciliation costs nothing — the duplicates are still there next cycle — and a stalled pass costs the run.

### R3 — A skill that is only reorganised was not reconciled

Rewriting headings, resorting an index and re-wording blocks produces a diff and no change in what any future task retrieves. It also invalidates nothing and helps nobody.

Report merges, references added, and retirements. If a cycle found no duplicates and nothing falsified, that is the correct outcome and the right thing to report.

### Using the tools (capability)

- Render the procedure with `phronix_learning_reconcile_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `subject`, `merged_subjects`, `merges`, `references`, `retirements`, `pointers`, `reorganised_only`) to `phronix_learning_reconcile_check`; a step is done only when the check passes.

## References

### X1 — Why one copy, and what a copy costs

Two blocks saying nearly the same thing are worse than either alone. A future retrieval gets both, cannot tell which is current, and a correction applied to one leaves the other confidently wrong — so the library degrades exactly where it was most used.

The single-copy rule is what makes the library correctable at all: one statement of a fact, one place to fix it, and every other mention a reference that follows the fix automatically.

## Constraints

- Change one block at a time through the skill tools; never hold a file open across a long deliberation (R2).
- Never retire an approach on a single failed attempt (I4).
- Do not merge a raced task's solution-<subject>-<plan> candidates (I1b).

## Corner cases

- Labels are stable and never recycled, so updating by label keeps last week's references resolving (I2).
- When you cannot tell whether the idea or the attempt failed, keep the lesson and record the doubt: wrongly kept costs one attempt, wrongly retired costs every future task (I4).
- Cases that turned out to be the same case are one case with two instances named (I1c).
- A learner that rewrites its own method every cycle is drifting; the bar is a pattern across cycles (I5).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_learning_reconcile_plan`, validator `phronix_learning_reconcile_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `subject_named` failed: work one subject at a time and name it (I1)
- `merges_keep_label` failed: each merge names the kept (already referenced) label and the folded one (I2)
- `merges_keep_specifics` failed: the merged block must still name the file, function and line of both specifics; summarising them destroys the skill (R0c, R1)
- `retirements_have_evidence` failed: name the observations that falsified it and whether the idea or only the implementation was ruled out (I4)
- `retire_idea_not_attempt` failed: a failed attempt does not falsify the approach: rewrite the lesson with what the code did instead of retiring it (I4)
- `pointers_for_merged_names` failed: leave each old subject name as a pointer skill to the topic (I1b)
- `not_reorganise_only` failed: report merges, references and retirements; a reorganisation alone changes nothing retrieved (R3)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- An unfinished reconciliation costs nothing: the duplicates are still there next cycle (R2).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A merge rule you keep applying by hand becomes a block in I2; a kind of finding nobody retrieves becomes a rule about what not to capture (I5).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Topic skill opening with the answer, then a case table (situation | what worked | what settled it), e.g. min_degrees int -> sum(powers.values()) in both loops of itermonomials -> target test fail->pass (phronix-learning-reconcile I1c, 2026-09-15).
- `phronix_learning_reconcile_plan` -> follow the checklist -> `phronix_learning_reconcile_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
