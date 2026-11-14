---
name: phronix_research_as_tools
description: Prefer calling an existing probe tool over re-deriving a fact by hand, and turn any deterministic procedure you are about to repeat (a reproduction, a measurement, a condition check) into a tool the next stage can call in one step, named for the question it answers. Load at the start of every research stage, when about to redo something already done in this pass, or when a stage is running out of budget on hand-derivations.
---
Cross-references: [[capability_builder]], [[knowledge]], [[phronix_capability_authoring]], [[phronix_build_solution]]

# Research is a tool-building exercise

Converted from the dftracer-agents skill `phronix-research-as-tools` (subject: prefer calling an existing probe tool over re-deriving a fact by hand, and turn any procedure you repeat into a tool the next stage can call in one step). Source description: Prefer calling an existing probe tool over re-deriving a fact by hand, and turn any procedure you repeat into a tool the next stage can call in one step.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's Rules ('If two people would do it identically, it is code in tool.py'; 'knowledge_search first, then capability_list'; 'Extend what exists') are I1/I2 in general form; this skill adds the research-budget reasoning and the probe_ naming rule. Candidate to merge into capability_builder.

# Research is a tool-building exercise

Every stage of research is under a hard budget, and a stage spends that budget
in two very different ways: *thinking*, which is what the budget is for, and
*re-establishing something already known*, which is what this skill exists to
eliminate.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Look for the tool before doing the work by hand |
| `I2` | Instructions | Build the tool the second time, not the fifth |
| `I3` | Instructions | Name it for the question, not the mechanism |
| `R1` | Rules | Why this is where the budget goes furthest |
| `R2` | Rules | The tool outlives the task |
| `X1` | References | Do not tool a one-off |

## Instructions

### I1 — Look for the tool before doing the work by hand

Before reproducing a failure, running a check, or extracting a fact from the
tree, call `capability_list` and see whether a `probe_` tool already does it.

A probe returns in one call what a hand-derivation costs five: open the file,
find the region, write a snippet, run it, read the output. Under a budget of
a hundred-odd seconds those five calls are most of the stage.

The store persists across tasks in the same repository, so the tool you want
was very likely built by an earlier task on this same subject.

### I2 — Build the tool the second time, not the fifth

The moment you find yourself about to do something you have already done in
this pass — or that the transcript shows another aspect doing — stop and call
`capability_new` instead.

Two things qualify, and nothing else does:

* **A deterministic procedure.** Same inputs, same answer, no judgement. A
  reproduction, a measurement, a check that a condition holds.
* **Something that will be asked again.** By the next aspect, the tune stage,
  a retry, or another task on this repository.

Judgement calls do not become tools. A tool that decides *whether an approach
is right* encodes one opinion as if it were arithmetic; a tool that *measures
what an approach does* is a fact, and the deciding stays where it belongs.

### I3 — Name it for the question, not the mechanism

`probe_ignore_paths_applied_recursively` says what it answers.
`probe_run_pylint` says what it runs, and the next stage cannot tell whether it
answers the question at hand without reading its source.

## Rules

### R1 — Why this is where the budget goes furthest

Tuning measures each approach against every instance of the corpus. That is the
same procedure run tens of times, and it is the single largest consumer of the
pass. Built as a tool it becomes tens of fast calls; done by hand it becomes
tens of multi-step derivations, and the stage is stopped by its budget
somewhere in the middle with most approaches unmeasured.

The pass that builds tools early is not slower for having done so. It is the
only version that finishes.

### R2 — The tool outlives the task

A probe is the most durable thing research produces. A skill records what was
believed and must be re-read and re-judged; a probe *runs*, and a later task
gets its answer without spending a stage on it.

This is why a tool built on the last try of a failing task is still worth
building. The task may be lost; the next one on that repository starts ahead.

### Using the tools (capability)

- Render the procedure with `phronix_research_as_tools_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `question`, `searched_existing`, `existing_probe`, `deterministic`, `uses_so_far`, `asked_again_by`, `decides_judgement`, `tool_name`, `built`) to `phronix_research_as_tools_check`; a step is done only when the check passes.

## References

### X1 — Do not tool a one-off

A procedure used once, in one task, that nothing will ask again is not a tool —
it is a shell command with ceremony around it. Every tool is listed to every
future agent, and a store full of single-use probes costs every later task the
time to read past them.

## Constraints

- Never build a tool that decides whether an approach is right (I2).
- Never tool a one-off (X1).
- Tools go through capability_new and the user's approval.

## Corner cases

- A hand derivation costs about five calls (open, find, snippet, run, read); under a budget of a hundred-odd seconds that is most of a stage (I1).
- The tool you want was very likely built by an earlier task on the same subject: the store persists across tasks in the same repository (I1).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_research_as_tools_plan`, validator `phronix_research_as_tools_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `question_stated` failed: state the question the step answers
- `searched_first` failed: knowledge_search and capability_list for a probe before doing it by hand (I1)
- `built_only_deterministic` failed: only a deterministic procedure becomes a tool; leave judgement in the skill (I2)
- `built_not_judgement` failed: a tool measures what an approach does; it never decides whether it is right (I2)
- `built_on_second_use` failed: build the tool the second time, not the first: a one-off is a shell command (I2, X1)
- `asked_again` failed: name who will ask again (next aspect, tune stage, retry, another task); otherwise do not tool it (X1)
- `named_for_question` failed: name it for the question it answers, not the command it runs (I3)
- `probe_prefix` failed: name probe tools probe_<question> (I3)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A probe returns a wrong answer: capability_update it with a failing check, do not redo it by hand (phronix_mcp_first).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A procedure done twice in a pass becomes a probe_ capability named for its question.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- capability_list first; build probe_<question> on the second use; tune with tens of probe calls instead of hand derivations (phronix-research-as-tools I1-I3, R1, 2026-09-15).
- `phronix_research_as_tools_plan` -> follow the checklist -> `phronix_research_as_tools_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
