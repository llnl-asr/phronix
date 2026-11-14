---
name: phronix_validate_exploration
description: Judge whether each explored idea actually answered its question (tried, what happened in numbers, what it rules in/out, not cut off); name the ones that came back thin or unattempted, with the specific missing piece, so they are explored again; let the rest through. Load after the explore stage files its findings, or when a validation pass starts narrating patches ('*** Begin Patch') or taking measurements itself.
---
Cross-references: [[phronix_explore_idea]], [[phronix_build_solution]], [[phronix_stage_finalize]], [[phronix_validate_ideas]]

# Judging whether explored ideas answered their questions

Converted from the dftracer-agents skill `phronix-validate-exploration` (subject: judge whether the explored ideas actually answered their questions). Source description: Judge whether the explored ideas actually answered their questions — name the ones that came back thin or unattempted so they can be explored again, and let the rest through.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

# Validating what the exploring found

Each idea was explored under a clock, and a stage that runs out of time files
what it had. Some of those findings answer their question and some do not. You
decide which, and you have no budget — you are reading findings, not making
them.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | A finding is complete when it answers its own question |
| `I2` | Instructions | Name what needs another pass, and why |
| `I3` | Instructions | A negative result is complete |
| `I4` | Instructions | Let it through when it is good enough |
| `X1` | References | Do not fill the gap yourself |
| `X2` | References | Do not write the fix |
| `R1` | Rules | Why this exists at all |

## Instructions

### I1 — A finding is complete when it answers its own question

Ask of each one:

* Was the idea actually **tried**, or only reasoned about? A finding with no
  evidence of running anything is a hypothesis wearing a finding's clothes.
* Does it say what **happened**, in numbers where there are numbers?
* Does it say what that **rules in and out**? A result nobody drew a conclusion
  from leaves the conclusion to the build stage, which has less context.
* Was it cut off? A finding that stops mid-measurement is explicitly partial and
  is the clearest case for another pass.

### I2 — Name what needs another pass, and why

For each idea that failed the check, say which of the above is missing. "Thin"
is not actionable; "tried the absolute form only, never the relative one, which
is the case the issue reports" tells the next pass exactly what to do.

An idea sent back is explored again with your reason attached, so the second
pass is not a repeat of the first.

### I3 — A negative result is complete

**An idea that was tried and did not work is finished.** It answered its
question. Sending it back because the answer was disappointing wastes a pass and
risks the second attempt manufacturing a positive result to satisfy you.

The same goes for an idea that turned out to be irrelevant: "this is not where
the problem is" is a real answer and it narrows the solution.

### I4 — Let it through when it is good enough

Every pass costs the wall clock that the budgets exist to bound. If the findings
between them let the solution be built, say so and stop — the build stage can
work from partial evidence and is required to mark what is unverified.

Send back only what would change the solution.

## Rules

### R1 — Why this exists at all

The explore stage is a prediction: that two minutes is enough to answer the
question. Sometimes it is not, and before this check the pipeline could not tell
the difference between "explored and answered" and "explored and ran out" — both
arrived as a filed finding, and the solution was built as if they were the same
thing.

### Using the tools (capability)

- Render the procedure with `phronix_validate_exploration_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `findings`, `patches`, `measurements_taken`) to `phronix_validate_exploration_check`; a step is done only when the check passes.

## References

### X1 — Do not fill the gap yourself

If a finding is missing its measurement, do not go and take the measurement.
That is exploring, it is budgeted, and doing it here hides the cost in a stage
that reports none. Name the gap and let the explorer close it.

### X2 — Do not write the fix

**No patches, no diffs, no code.** You have no editing tools, and writing a
patch as text does not become one — it is output nobody applies, produced by a
stage with no clock, while the actual verdict goes unrecorded.

Measured: thirty-five `*** Begin Patch *** Update File: ...` blocks from a
single validation pass. The model could not edit, so it narrated edits instead.

If you find yourself reaching for a patch, that is the signal the finding is
already complete enough to build from. Record that it is complete and stop.

## Constraints

- No budget, but no exploring: read findings, do not make them (X1).
- No editing tools; no narrated patches (X2).
- Send back only what would change the solution (I4).

## Corner cases

- A finding cut off mid-measurement is explicitly partial and the clearest case for another pass (I1).
- 'This is not where the problem is' is a real answer and narrows the solution (I3).
- Reaching for a patch is the signal the finding is complete enough to build from: record that and stop (X2).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_validate_exploration_plan`, validator `phronix_validate_exploration_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `findings_judged` failed: judge every finding: verdict complete or again (I1)
- `verdicts_known` failed: verdict is 'complete' or 'again'
- `sendback_missing` failed: every 'again' names what is missing: what was tried, what happened, what it rules out, or that it was cut off (I1, I2)
- `sendback_reasons` failed: every 'again' names what is missing (tried|happened|rules|cut off) and a reason specific enough for the next pass, e.g. 'tried the absolute form only, never the relative one' (I2)
- `negatives_complete` failed: a tried-and-did-not-work idea is finished; do not send it back for being disappointing (I3)
- `no_patches` failed: no patches, diffs or code: record that the finding is complete and stop (X2)
- `no_measurements` failed: do not take the measurement yourself; name the gap for the explorer (X1)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A verdict pass killed before recording: record verdicts as soon as each finding is judged.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A recurring kind of thin finding (e.g. never tried the relative form) is a lesson for [[phronix-explore-idea]].
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Four completeness questions per finding; specific send-back reasons; negatives complete (2026-09-15).
- `phronix_validate_exploration_plan` -> follow the checklist -> `phronix_validate_exploration_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
