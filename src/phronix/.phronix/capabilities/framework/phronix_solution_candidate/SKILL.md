---
name: phronix_solution_candidate
description: Write the solution skill for ONE researched approach so rival approaches can be tried against the real tests and compared fairly: ordered steps a stranger can execute, a tool per step where one exists, a check per step, the approach stated at its fairest. Load when a research pass hands you one approach to write up as a candidate, or when a candidate skill reads as a story ('we concluded', 'investigate whether') instead of steps.
---
Cross-references: [[phronix_skill_authoring]], [[phronix_trial_reconcile]], [[phronix_research_plan]], [[phronix_build_solution]]

# Turning one researched approach into an executable solution skill

Converted from the dftracer-agents skill `phronix-solution-candidate` (subject: turning one researched approach into an executable solution skill). Source description: Write the solution skill for ONE researched approach, so that rival approaches can be tried against the real tests and compared fairly — steps a stranger can execute, not an account of the reasoning.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Write steps, not the story |
| `I2` | Instructions | A tool per step wherever one exists |
| `I3` | Instructions | Every step carries its own check |
| `R1` | Rules | Give your approach its fairest statement |
| `R2` | Rules | Short, because every block is read forever |
| `R3` | Rules | Yours is kept and linked, whatever the outcome |
| `X1` | References | Why the write-ups are written in parallel |

## Instructions

### I1 — Write steps, not the story

An agent that has never seen this task will be handed your skill and nothing else, and must produce the fix from it. It cannot ask you what you meant.

So write what to *do*, in order. Not what you concluded, not why the approach is promising, not what you ruled out — those belong in the research record, and this skill is the part someone executes.

### I2 — A tool per step wherever one exists

Name the tool and its arguments. A step that says "check whether the path is normalised" is a step the reader has to design; `probe_ignore_paths_matrix(path=...)` is one they can run.

Where no tool fits, write one instruction a reader can follow without inferring anything. If you find yourself writing "investigate whether", that is research leaking into a solution — decide it now, or build the tool that decides it.

### I3 — Every step carries its own check

Say what proves the step worked. A failure then surfaces at the step that caused it, rather than at the end where everything looks equally suspect.

This is what makes a losing approach useful: a skill that fails at step 2 with a clear check tells you the approach is wrong; one that fails at the end tells you nothing.

## Rules

### R1 — Give your approach its fairest statement

Other agents are writing the skills for the rival approaches at the same time, and all of them will be tried against the real tests. Do not hedge toward the others or soften a claim you believe.

A strong idea losing to a weak write-up corrupts the comparison, and the comparison is the point: it is the only thing that tests whether the research metric ranked them correctly.

If your approach turns out to be wrong, that is a result. Say so plainly rather than quietly widening the skill until it covers someone else's idea.

### R2 — Short, because every block is read forever

Every block is read on every future retrieval of this skill. A step nobody can act on costs context on every task that loads it.

Lead with the action. One idea per block. Split rather than combine.

### R3 — Yours is kept and linked, whatever the outcome

Your skill is not scaffolding to be thrown away when the trials are scored. When
every candidate has been tried, the subject's own skill is merged out of them
and links back to each one — including the ones that lost.

So write it to stand on its own. A reader who follows that link is asking "was
this tried, and what happened?", and the answer has to be here rather than
restated in the merged skill. That is what makes a losing candidate worth
keeping: an idea recorded with the check that killed it costs the next task a
sentence, and an unrecorded one costs it an attempt.

### Using the tools (capability)

- Render the procedure with `phronix_solution_candidate_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `approach`, `steps`, `wrong_if`) to `phronix_solution_candidate_check`; a step is done only when the check passes.

## References

### X1 — Why the write-ups are written in parallel

Research ranks approaches against a figure of merit measured on a corpus it built itself — a proxy. The top-ranked approach is the most promising one, not the correct one.

Trying several against the task's own tests is what settles it, and that is affordable because the attempts are independent: N approaches cost wall clock once rather than N times. What it requires is that each approach arrive as its own skill, which is this skill's job.

## Constraints

- Write one approach only; never hedge toward or absorb the rival approaches (R1).
- No story: what was concluded, why it is promising, what was ruled out stay in the research record (I1).

## Corner cases

- A strong idea losing to a weak write-up corrupts the comparison, which is the only test of whether the research metric ranked approaches correctly (R1).
- A skill that fails at step 2 with a clear check says the approach is wrong; one that fails at the end says nothing (I3).
- Research ranks approaches on a proxy figure of merit on its own corpus; trying several against the task's tests settles it, affordable because attempts are independent (X1).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_solution_candidate_plan`, validator `phronix_solution_candidate_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `one_approach` failed: name the ONE approach this candidate states
- `steps_present` failed: write what to DO, in order (I1)
- `each_step_has_check` failed: every step carries its own check: what proves it worked (I3)
- `no_research_leak` failed: 'investigate whether' is research leaking into a solution: decide it now, or build the tool that decides it (I2)
- `falsifiable` failed: say which step's check failing shows the approach is wrong, so a losing candidate is informative (I3, R3)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A step with no tool and no unambiguous instruction: build the tool (capability_new) rather than writing 'investigate whether'.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A losing candidate is kept and linked from the subject's merged skill ([[phronix-trial-reconcile#R2b]]); write it to stand on its own (R3).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Candidates written as tool-call steps each with a check, tried in parallel against the real tests, then reconciled ([[phronix-trial-reconcile]]) (2026-09-15).
- `phronix_solution_candidate_plan` -> follow the checklist -> `phronix_solution_candidate_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
