---
name: phronix_task_tracker
description: Keep one task's tracker.md (The problem, How it has been approached, What worked, What did not work, Notes), rewritten and reorganised after every phase (attempt, evaluation, research pass) so nothing is lost, nothing appears twice, and every line traces to evidence. Load after each phase of a task, when a tracker grows shorter or more optimistic each pass, mixes two task ids, or lists the same finding several times ('attempt, attempt, attempt').
---
Cross-references: [[phronix_task_research]], [[knowledge]], [[lessons]]

# Keeping one task's running record

Converted from the dftracer-agents skill `phronix-task-tracker` (subject: keeping one task's running record). Source description: Keep one task's running record — the problem, how it has been approached, what worked and what did not — reorganised after every phase so nothing is lost and everything is where the next phase will look for it.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** The lessons capability's 'one copy of each fact; a near-duplicate is refused' and consolidation (lesson_merge keeping every fact) are the store-wide form of I2/R2 here (merge, never discard, a repeat is a count); tracker.md itself is per-task memory, not a lesson.

# Tracking one task

You maintain `tracker.md` for **this task and no other**. It is the task's
memory: everything the system knows about solving *this* problem, and nothing
about any other.

You are called after every phase — after an attempt, after an evaluation, after
a research pass. Each time, you fold what just happened into the record and
reorganise it. You do not attempt the task, you do not fix anything, and you do
not research. Recording is the whole job.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The shape: problem, approach, what worked, what did not |
| `I2` | Instructions | Reorganise every time. Never discard. |
| `I3` | Instructions | Record evidence, never impressions |
| `I4` | Instructions | One task. Never carry another task's record into this one |
| `R1` | Rules | Never delete a failure that is still true |
| `R2` | Rules | Nothing appears twice; a repeat is a count, not a new entry |


## Instructions

### I1 — The shape: problem, approach, what worked, what did not

Four sections, in this order, because the next phase reads from the top and may
not reach the bottom:

```markdown
# <task id>

## The problem
<what is actually being solved, in two or three lines — restated from the
evidence, not copied from the issue>

## How it has been approached
- <attempt/pass> -> <what it tried, in one line>

## What worked
- <what is confirmed, and what confirmed it>

## What did not work
- <what was tried> -> <what happened> -> <why it is not the answer>

## Notes
- <anything that does not fit above, and is worth one line>
```

**The problem** goes first and is restated each pass. By the second attempt it
is not the issue text any more — it is "the email is in the hash but a custom
user model has no `email` attribute". A phase that starts from the issue when
half of it is solved re-solves the half that is done.

**How it has been approached** is what stops the loop going round. One line per
attempt or pass: what it tried, not how it went. A later phase reading this can
see at a glance that a direction has been taken already.

**What worked** is banked. A target test that was failing and now passes belongs
here, with the evidence. So does a fact something demonstrated — "the email must
come from `get_email_field_name()`" — once a result showed it.

**What did not work** is the other half of not repeating yourself, and it needs
the *why*. An entry without one reads as "not tried hard enough" and gets tried
again.

### I2 — Reorganise every time. Never discard.

Every call rewrites the whole file. You are not appending to the end of it, and
you are not shortening it either.

**Nothing is dropped.** A detail recorded three phases ago is a detail the next
phase does not have to rediscover, and you cannot know which one that will be.
An error message, a line number, a version, a flag that did not work — these
are cheap to keep and expensive to re-derive.

What you do instead is put things where they belong:

* Two entries about the same thing become ONE entry holding both facts — not
  one of them chosen over the other.
* An entry that a later result explains gets that explanation attached to it,
  in place. `getattr(user, 'email', '')` returned empty stays, and gains
  "because CustomEmailField names the field `email_address`".
* An entry under the wrong heading moves. A thing believed to work that a test
  then contradicted moves from **What worked** to **What did not work**, with
  what contradicted it.
* Ordering carries meaning: within each section, most recent last, so a reader
  can see how the understanding moved.

The record grows, and that is correct — it is the task's memory, and a task
that has been worked four times knows more than one worked once. What must not
grow is DISORDER: four attempts' worth of notes under one heading in the order
they happened is a transcript, and the transcript already exists.

If a section becomes long, that is a signal to group within it — sub-bullets
under the thing they are about — not to delete.

### I3 — Record evidence, never impressions

Every line traces to something that happened: a test result, an error, a diff.

* **Good:** ``What did not work — `user.email` in the hash -> TypeError: must
  be str, not NoneType at tokens.py:99 -> a CustomEmailField model has no
  `email` attribute``
* **Bad:** "the email handling needs more work"

The second is a feeling. The next phase cannot act on it, and it survives every
reorganisation because nothing ever contradicts it.

If an attempt produced no evidence — it ran and changed nothing, or it died —
record *that*, in one line, under `Notes`. An attempt that produced nothing is a
fact about the task.

### I4 — One task. Never carry another task's record into this one

The record is per task, and the isolation is the point. Two tasks that look
alike are still two tasks: an "established" fact from one is an assumption in
the other, and an assumption presented as established is worse than nothing,
because the next phase will not re-check it.

If you are given a record that mentions a different task id, say so and start a
new one rather than merging them.

What crosses task boundaries is a SKILL, written deliberately at the end from
what this record established — not the record itself.

## Rules

### R1 — Never delete a failure that is still true

Reorganising moves things and merges things. It does not remove them.

An entry under `What did not work` MOVES only when something has changed it:
the test now passes, or a later result showed the reason was wrong — and then
it moves to the section that is now true of it, carrying the evidence that
moved it. "It has been there a while" is not a reason, and neither is the
record being long.

The failure mode this prevents is a record that gets shorter and more optimistic
every pass until it says the task is nearly solved. Measured elsewhere in this
system: an agent reading a patched working tree concluded "the implementation is
complete and correct" while a target test was failing. A record that had kept
the failing test in front of it could not have agreed.

### R2 — Nothing appears twice; a repeat is a count, not a new entry

If a phase repeats a finding the record already holds, add a count to the existing entry rather than writing another one. Two entries saying the same thing are not two results.

What it costs to get this wrong: a record with one finding written three times takes three reads to learn one thing, and the next attempt cannot tell whether three approaches were tried or one approach was tried three times — which is exactly the question it opens the record to answer. Measured on a live fold, one cycle handed the tracker `attempt, attempt, attempt` for three runs of the same stage.

The same holds for the history the solution skill links to: it is read by every later attempt on this subject, so a duplicated entry is paid for again on every one of them.

### Using the tools (capability)

- Render the procedure with `phronix_task_tracker_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `task_id`, `problem`, `approached`, `worked`, `did_not_work`, `notes`, `other_task_ids`) to `phronix_task_tracker_check`; a step is done only when the check passes.


## Constraints

- Do not attempt, fix or research: recording only.
- Rewrite the whole file each call; never append-only, never shorten (I2).
- Never merge two task ids (I4).
- Never drop a still-true failure because the record is long or it is old (R1).

## Corner cases

- A thing believed to work that a test then contradicted moves to What did not work, with what contradicted it (I2).
- An entry a later result explains keeps its text and gains the explanation in place, e.g. getattr(user, 'email', '') returned empty -> because CustomEmailField names the field email_address (I2).
- A long section is grouped with sub-bullets, never trimmed (I2).
- The previous version's What-did-not-work entries must be compared by hand with the new ones: the validator only sees one version (R1).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_task_tracker_plan`, validator `phronix_task_tracker_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `task_id` failed: the record is for one named task (I4)
- `problem_restated` failed: restate The problem from the evidence each pass (I1)
- `approaches_listed` failed: one line per attempt/pass under How it has been approached (I1)
- `failures_have_why` failed: each What-did-not-work entry is '<tried> -> <happened> -> <why it is not the answer>' (I1, I3)
- `no_impressions` failed: replace impressions with the test result, error or diff behind them (I3)
- `single_task` failed: the record mentions another task: start a new record rather than merging (I4)
- `no_duplicates` failed: an entry appears twice: make the repeat a count on the existing entry (R2)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A tracker that lost entries: rebuild it from the previous versions and the attempt summaries, keeping every fact.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- What crosses task boundaries is a skill written deliberately from what the record established, not the record (I4).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Whole-file rewrite into five fixed sections, most recent last, repeats counted, failures with why (2026-09-15).
- `phronix_task_tracker_plan` -> follow the checklist -> `phronix_task_tracker_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
