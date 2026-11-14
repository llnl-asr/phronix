---
name: phronix_trial_reconcile
description: After several approaches were tried against the real tests: read the table as evidence about the research ranking, write the subject's solution skill from what the passing ones agree on (or the winner's spine plus what losers did better), carry every failure forward as a named corner case, record which step failed (research_record_step_reached), and when none worked find the assumption all of them shared. Load after parallel trials finish, when tempted to refine the least-bad candidate, or when every candidate scored 0.
---
Cross-references: [[phronix_solution_candidate]], [[phronix_skill_authoring]], [[phronix_research_plan]], [[phronix_build_solution]]

# Reconciling the results of parallel solution trials

Converted from the dftracer-agents skill `phronix-trial-reconcile` (subject: reconciling the results of parallel solution trials). Source description: What to do after several approaches have been tried against the real tests — merge the winner with whatever the losers did better, or, when none worked, find the assumption all of them shared.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Read the table as evidence about the ranking |
| `I2` | Instructions | Something worked: merge, keeping the winner's spine |
| `I2b` | Instructions | Exactly one worked: merge, keeping the winner's spine |
| `I3` | Instructions | Nothing worked: find the shared assumption |
| `I3b` | Instructions | Carry every failure forward as a named corner case |
| `I3c` | Instructions | Say WHICH STEP failed, and record it |
| `I4` | Instructions | Score the result on outcome, cost, and transfer |
| `R1` | Rules | A losing approach is not wrong in every part |
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R2b` | Rules | The subject's skill is the way in to the candidates |
| `R2` | Rules | Do not refine the least-bad candidate |
| `X1` | References | Why all-failed is the more informative case |

## Instructions

### I1 — Read the table as evidence about the ranking

You are given one row per approach: which plan, how far it got on the task's own target tests, whether it solved it.

That table has already tested something research could only estimate. Approaches were ranked before any of them was attempted, against a figure of merit measured on a corpus research built itself. The trials tested that ranking against the real tests, and the table says whether it was right.

Record that. "The metric ranked B first and C solved it" is a finding about the metric, and the next task on this subject inherits it.

### I2 — Several passed: the solution is what they agree on

More than one candidate passing the benchmark's own tests is the best evidence a
research pass can produce — several independent readings of the problem, each
tried against the real target tests, each verified rather than argued.

Write the solution skill out of the ones that **passed**:

- what they have in common is the fix. If two passing candidates both change
  the same function in the same direction, that is the answer, and it is
  confirmed twice.
- where they differ, prefer the smaller change. Both passed, so the extra work
  in the larger one bought nothing measurable.
- record that it was confirmed by more than one candidate. A later task should
  know the difference between "this worked once" and "three readings converged
  on this".

The ones that **failed** become lessons in the same skill, one line each, saying
what was tried and what the tests showed. Be precise about what failed: the
implementation, or the idea. An attempt whose code did not fire tells you about
the code — writing "this approach does not work" retires an idea that was never
tested, and every later task inherits that.

### I2b — Exactly one worked: merge, keeping the winner's spine

`skill_load` the winning approach's skill and the losers'. Write ONE skill for this subject:

- the winner's steps are the spine — they are what produced the fix;
- fold in anything a loser did **better**: a cheaper check, a more direct tool call, a step that generalises where the winner's is specific;
- retire the rest by name, one line each on what the tests showed.

Merging is not concatenation. A merged skill that contains every step of every approach is longer, slower and no more correct than the winner alone.

### I3 — Nothing worked: find the shared assumption

Do not pick the least-bad and refine it. That is the one move that cannot find the problem.

Several independent approaches failing is evidence about the **subject**: they share something false. Work it in this order:

1. Name what every approach took for granted — the file that produces the behaviour, the shape of the fix, what the test is actually asking for. Write it as a claim that could be false.
2. Check that claim with a command whose output settles it. A run, not an argument.
3. Say which of the failures the claim explains. One that explains one failure out of four is probably not it.
4. Then produce candidates against the corrected understanding and record them with `research_add_approach`.

### I3b — Carry every failure forward as a named corner case

You are holding the one thing no later reader will have: a table of what was
tried and what each attempt scored. A losing candidate is a wrong reading that
someone actually had, and the merged skill is where it becomes a warning.

For each candidate that failed, write into the skill: what it did, why it looked
right, and what it scored. Name the specific construct, site or subset — not
"be careful with exceptions" but "converting only `Blueprint.__init__` and not
the two `add_url_rule` sites scores 1/2, not partial credit toward 2/2".

Discarding this is how the next model repeats an attempt you already paid for.
[[phronix-skill-authoring]] `R0c` carries the measured case.

### I3c — Say WHICH STEP failed, and record it

The plan is an ordered method — see [[phronix-research-plan]] `I5b` — so a
failure has a position, and finding it is the most useful thing this stage does.

Read the test output against the steps: which step's expectation was the first
not to hold? Then:

```
research_record_step_reached(topic, "<step name>", "<what the output showed>")
```

Why this matters more than it looks. "0 target tests passing" is the same number
on try 1 and try 3, so a task that is converging looks identical to one that is
stuck, and both are stopped at the same ceiling. A position does distinguish
them: failing at step 2, then at step 4, is progress — and a task that shows it
is granted another try rather than being cut off while closing in.

It also aims the next pass. A whole-fix retry re-derives everything; a retry that
knows step 3 was where it broke keeps steps 1 and 2 and looks for another way to
do step 3 — which is what [[phronix-research-plan]] `I5b` set the method up for.

Be honest about which step. If the failure is that the steps do not compose, or
that a step nobody planned was needed, say that instead of picking the nearest
name — a wrong attribution moves the next pass away from the problem, and the
progress signal then rewards noise.

### I4 — Score the result on outcome, cost, and transfer

State all three plainly for whatever you write, in this order:

| | what to say |
| --- | --- |
| outcome | does it produce the fix, on this task's tests |
| cost | roughly how many tokens and how long |
| transfer | how much would still apply to a DIFFERENT task in this subject |

A skill that solves one instance and generalises to none is worth less than a slightly slower one that transfers. The next task inherits the skill, not the instance.

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

### R2b — The subject's skill is the way in to the candidates

Every candidate wrote its own skill and keeps it. The subject's skill links to
each one with `[[name]]`, one line saying what that idea was and what the tests
did with it.

Link them all, winners and losers. A reader who wants the answer stops at the
solution; one asking "was X tried?" follows the link and finds the whole
attempt, including the failed ones — which is the question a later task on this
subject actually arrives with.

Do not copy the candidates in. Four write-ups pasted together is not a solution,
it is the same reading problem the merge exists to solve. Carry the fix and the
map; leave the detail where it was written.

### R1 — A losing approach is not wrong in every part

They failed as wholes. A candidate that got two of three target tests passing had most of it right, and discarding it entirely throws that away.

Take the parts that were measured to work. Say which trial each borrowed step came from, so a later correction knows what it is correcting.

### R2 — Do not refine the least-bad candidate

When every approach fails, the tempting move is to take the one that got furthest and adjust it. It feels like progress and is the reason a task can burn every retry without the diagnosis moving.

Furthest is not closest. An approach that passes two tests by coincidence of ordering is not nearer the fix than one that passes none for a comprehensible reason.

### Using the tools (capability)

- Render the procedure with `phronix_trial_reconcile_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `ranking_finding`, `passed`, `candidates`, `branch`, `shared_assumption`, `assumption_check`, `corner_cases`, `step_reached`, `links`, `outcome`, `cost`, `transfer`, `instructions`) to `phronix_trial_reconcile_check`; a step is done only when the check passes.

## References

### X1 — Why all-failed is the more informative case

One approach failing says that approach was wrong. Four independent approaches failing says something they all believed was wrong — and that is a much stronger, much more useful signal, because it points at the subject rather than at a candidate.

The cost of missing it is high: the shared assumption survives into every later attempt, and the research record grows more detailed and more confident about the wrong area. Learning turns exploration into conviction, and this is the moment to prevent that.

## Constraints

- Do not concatenate candidates into the merged skill; carry the fix and the map (I2b, R2b).
- Do not write 'this approach does not work' when only the implementation failed (I2).
- Do not pick the nearest step name when the real failure is that steps did not compose (I3c).

## Corner cases

- Several passing: prefer the smaller change where they differ; the larger one's extra work bought nothing measurable (I2).
- '0 target tests passing' is the same on try 1 and try 3; the failing step position distinguishes converging from stuck (I3c).
- An approach passing two tests by coincidence of ordering is not nearer the fix than one passing none for a comprehensible reason (R2).
- Four independent failures point at the subject, not a candidate: the shared assumption would otherwise survive into every later attempt (X1).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_trial_reconcile_plan`, validator `phronix_trial_reconcile_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `ranking_recorded` failed: record what the table says about the research metric's ranking (I1)
- `branch_known` failed: branch is several, one or none passed
- `assumption_stated` failed: none passed: name the assumption every approach shared, as a claim that could be false; do not refine the least-bad (I3, R2)
- `assumption_checked` failed: check the shared assumption with a command whose output settles it (I3 step 2)
- `failures_carried` failed: carry each failed candidate forward as a named corner case with what it scored (I3b)
- `step_recorded` failed: record which step failed with research_record_step_reached (I3c)
- `candidates_linked` failed: link every candidate skill with [[name]], winners and losers (R2b)
- `outcome_cost_transfer` failed: state outcome, cost and transfer, in that order (I4)
- `instructions_present` failed: the merged skill's Instructions must carry the fix (R0)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- research_record_step_reached refused: check the topic and step name exist in the plan ([[phronix-research-plan#I5b]]).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- The ranking finding (metric vs real tests) is inherited by the next task on this subject: record it (I1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Branch on pass count; winner's spine + losers' better parts; all candidates linked; failing step recorded (2026-09-15).
- `phronix_trial_reconcile_plan` -> follow the checklist -> `phronix_trial_reconcile_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
