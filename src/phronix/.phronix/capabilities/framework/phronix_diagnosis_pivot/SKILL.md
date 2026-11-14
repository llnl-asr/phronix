---
name: phronix_diagnosis_pivot
description: What to do when two attempts have failed in exactly the same way (same tests, same reason, same text missing): stop refining the change, name what both attempts assumed as a falsifiable claim, check the edits even run, read the assertion literally, and take a genuinely different path. Load on a second identical failure, when a retry differs only in values/indentation/names, or when a fix keeps 'improving' while the outcome never changes.
---
Cross-references: [[phronix_learn_from_attempt]], [[phronix_trial_reconcile]], [[phronix_self_research]], [[capability_builder]]

# Pivoting after two identical failures

Converted from the dftracer-agents skill `phronix-diagnosis-pivot` (subject: diagnosing a failure that has stopped moving). Source description: What to do when two attempts have failed in exactly the same way — stop refining the change, name what both attempts assumed, and take a genuinely different path.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's and every store skill's Corrector say 'the same failure twice stops the loop: change approach, or ask'; this skill is the method for changing approach. Complementary; could be referenced from capability_builder's Corrector.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Name the assumption, as a claim that can be false |
| `I2` | Instructions | Check whether your edits even run |
| `I3` | Instructions | Read what the test asks for, literally |
| `I4` | Instructions | Take a different path, and say why it differs |
| `R1` | Rules | An identical failure is evidence, not noise |
| `R2` | Rules | The same edit with better values is not a new approach |
| `X1` | References | What this looks like when it goes wrong |

## Instructions

### I1 — Name the assumption, as a claim that could be false

Ordinary diagnosis asks what was missing, which assumes the last attempt was close. Two identical failures are exactly the evidence against that assumption, so start somewhere else.

Write down what both attempts took for granted, as a claim someone could disprove:

- "the header text is right and only the layout is wrong"
- "this function is the one that produces the output"
- "the test fails because the value is wrong, not because it is absent"

You cannot pivot away from an assumption you have not stated.

### I2 — Check whether your edits even run

Before anything else, confirm the code you changed is executed on this path. A print, a breakpoint, a deliberate exception — something that cannot be true unless your edit runs.

An identical failure across two different patches is the signature of edits that never took effect: a different module shadowing the one you edited, an installed copy rather than the checkout, a branch that is never reached.

### I3 — Read what the test asks for, literally

Take the assertion apart word by word. A containment assertion wants an exact string; a comparison wants an exact value; an exception test wants that exception type and not a subclass.

The failure output usually says both halves — what was wanted and what was produced. Where they differ by a word, the word is the bug. Two capable models have independently written a column named `Domain` while the test asked for `Subdomain`, each refining the logic three times without reconsidering the string.

### I4 — Take a different path, and say why it differs

A different file, a different mechanism, or a different reading of what the test wants. Then state, in one line, what makes it different from what already failed twice.

If you cannot say that, you have not pivoted. `research_ruled_out` lists what has been tried; none of it is worth repeating unchanged.

## Rules

### R1 — An identical failure is evidence, not noise

Same tests, same reason, same text missing. That is a measurement, and it says the idea is wrong rather than the execution.

Treating it as bad luck — retrying, adjusting values, tidying the change — spends the remaining attempts on a question that has already been answered.

### R2 — The same edit with better values is not a new approach

Re-indenting it, moving it, renaming a variable, changing a constant: all the same approach. The check is whether the change would still fail for the reason the last one did.

If your new plan leads back to an edit that has already failed, the diagnosis is what is wrong. Go back to `I1`.

### Using the tools (capability)

- Render the procedure with `phronix_diagnosis_pivot_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `failure`, `assumption`, `edits_run`, `wanted`, `produced`, `new_path`, `differs_because`, `same_edit`) to `phronix_diagnosis_pivot_check`; a step is done only when the check passes.

## References

### X1 — What this looks like when it goes wrong

Measured on one task: three attempts added a CLI column, each improving the logic — unconditional, then conditional, then handling host-versus-subdomain correctly — and every one named the column `Domain` while the tests asserted `Subdomain` and `Host`. The mechanism got better each time and the outcome never changed.

Measured on another: every block the learner wrote was about the wrong file entirely, and each attempt saw only that its own patch failed, never that three patches in the same function had failed. The knowledge base grew more detailed and more confident about the wrong area.

Both are the same failure: refinement continuing past the point where the evidence stopped supporting the approach.

## Constraints

- Do not retry, adjust values or tidy the change after an identical failure (R1).
- Do not repeat anything research_ruled_out lists unchanged (I4).

## Corner cases

- An identical failure across two different patches is the signature of edits that never took effect: a shadowing module, an installed copy rather than the checkout, an unreached branch (I2).
- A containment assertion wants an exact string; a comparison an exact value; an exception test that exception type, not a subclass (I3).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_diagnosis_pivot_plan`, validator `phronix_diagnosis_pivot_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `failure_quoted` failed: quote the identical failure (tests, reason, missing text)
- `assumption_stated` failed: state what both attempts assumed, as a claim that could be false (I1); you cannot pivot away from an unstated assumption
- `edits_proven_to_run` failed: prove whether the edited code executes on this path (print/breakpoint/deliberate exception) (I2)
- `test_read_literally` failed: write what the assertion wants, literally (I3)
- `produced_recorded` failed: write what the code produced next to what was wanted (I3)
- `new_path` failed: name the different file, mechanism or reading of the test (I4)
- `differs_stated` failed: say in one line what makes the new path different from what failed twice; if you cannot, you have not pivoted (I4)
- `not_same_edit` failed: the same edit with better values is not a new approach: go back to I1 (R2)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- The new path leads back to a failed edit: the diagnosis is wrong; restart at I1 (R2).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A pivot that worked: record what the failed attempts assumed and what the different path was (phronix_learn_from_attempt I3: say what failed, not what to abandon).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Name the assumption, prove the edit runs, diff wanted vs produced, pivot with a one-line difference (phronix-diagnosis-pivot I1-I4, 2026-09-15).
- `phronix_diagnosis_pivot_plan` -> follow the checklist -> `phronix_diagnosis_pivot_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
