---
name: phronix_build_solution
description: Turn what the explored ideas found into the solution: a skill holding a pipeline of steps, with every deterministic step built as an MCP tool (capability_new) and only the judgement left as prose. Load after the exploration of (three) ideas against a real failure is finished, when writing the solution skill, or when a solution skill has an empty Instructions section, cites labels that do not resolve, opens with 'research on <repo>' instead of the problem, or describes the bug without the fix.
---
Cross-references: [[capability_builder]], [[phronix_skill_authoring]], [[phronix_explore_idea]], [[phronix_research_as_tools]], [[phronix_solution_candidate]]

# Building the solution from explored ideas

Converted from the dftracer-agents skill `phronix-build-solution` (subject: turn what the explored ideas found into the solution). Source description: How to turn what the explored ideas found into the solution — a skill holding a pipeline of steps, with every deterministic step built as an MCP tool and only the judgement left as prose.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder's first rule ('if two people would do it identically, it is code in tool.py; prose carries only what needs judgement') and its composite-capability section (a complex procedure split into step capabilities, the parent's skill lists them in order) are I1-I3 here. The solution-skill specifics (symptom/case/cause opening, corner cases from the trials, no clock, no exploring) are not in the store.

# Building the solution

Three ideas were explored against a real failure. Your job is to turn what they
found into the thing a later task can actually use: a skill that holds a
**pipeline** for solving this task, step by step.

There is no time limit on this. Every minute the pipeline spent was spent to
produce your input, and a solution cut off half-written wastes all of it.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The output is a pipeline, not an essay |
| `I2` | Instructions | Every deterministic step becomes an MCP tool |
| `I3` | Instructions | Only what needs judgement stays as a skill |
| `I4` | Instructions | Build from all three findings, including the failures |
| `I5` | Instructions | Say which problem it solved, in the skill's own words |
| `I5b` | Instructions | List the corner cases before you finish |
| `I6` | Instructions | Attach it so it will be found |
| `X1` | References | Do not explore here |
| `R0` | Rules | A skill that solves a problem must say how to solve it |
| `R1` | Rules | Why this stage has no clock |

## Instructions

### I1 — The output is a pipeline, not an essay

The skill says how to solve the task as an ordered sequence of steps. Each step
is one thing done, with a way to tell whether it worked.

A description of the bug is not a solution. "The filter uses max instead of sum"
is a finding; the solution is the sequence that locates it, changes it, and
demonstrates the change is right.

### I2 — Every deterministic step becomes an MCP tool

This is the part that matters most, and the part most easily skipped.

A step is deterministic when the same inputs give the same answer and no
judgement is involved: reproducing the failure, locating a call site, applying a
known edit, running a check, comparing before and after. **Build it with
`capability_new`.**

Prefer a tool for as much of the pipeline as can be made into one. A pipeline of
five tool calls runs in seconds on the next task; the same pipeline written as
five paragraphs of instructions costs a later agent five multi-step
derivations, and it will get one of them subtly wrong.

Name each tool for the question it answers, not the command it runs.

### I3 — Only what needs judgement stays as a skill

What is left after the tools are built is the part a tool cannot hold: which
step to take when the check comes back ambiguous, what the trade-off is between
two fixes, what to look at when the reproduction does not reproduce. Write that
as the skill's prose, and keep it to what a competent agent could not work out
alone.

If a step reads as prose but has one correct answer given its inputs, it is a
tool you have not built yet.

### I4 — Build from all three findings, including the failures

An idea that failed removes a direction, and a pipeline that does not mention it
invites the next attempt straight back into it. Say what was tried and did not
work, in one line each, where the pipeline would otherwise tempt someone into
it.

**Say what failed, not what to abandon.** An attempt that implemented an idea
badly has told you about the implementation, not the idea. Write *"the check
was added to `Blueprint.__init__` and did not fire for the path the test
uses"* — not *"dot validation does not work"*. The second sentence, written
once, rules the correct answer out of every future task on this repository.

Where two ideas found parts of the answer, the solution is their combination —
that is the reason three are explored rather than one.

### I5 — Say which problem it solved, in the skill's own words

Open the skill with the problem it solves, concretely enough that a later agent
can tell at a glance whether it has the same one:

* the **symptom** — what was observed to be wrong
* the **case** — the failing test or the smallest input that shows it
* the **cause** — where in the code the behaviour comes from

This is the most important paragraph in the file, because it is what a later
task reads first and what it decides on. A skill that opens with "research on
flask" tells the next agent nothing except that it is about Flask, and a skill
retrieved on that basis is a skill applied to the wrong bug.

It also removes the need for anything to guess. Say what you solved, and the
reader can tell whether it is their problem — no matching heuristic in the
middle deciding for them, and no confident answer when the truth is "related,
but not the same".

### I5b — List the corner cases before you finish

Go back through the pipeline you just wrote and, for every step, answer: what
will a smaller model plausibly write instead of this, and why would that fail?
Write each answer into the skill next to the step it protects.

You have the evidence to do this and nobody downstream does — you watched the
trials. Every candidate that failed is a wrong reading somebody actually had, so
say what it was and what it cost:

* the construct that looks equivalent and is not (`assert` where the test wants
  `raise ValueError`; `==` where the code needs `is`)
* the subset that looks sufficient and is not — name each site the fix needs,
  and say what applying only some of them scores
* the neighbouring style that will be copied — "the `assert`s already in this
  function are exactly what must change"
* the test that a CORRECT fix breaks, so the reader does not treat their own
  right answer as a mistake and undo it

Be specific to this task. Anything you write that would still be true of a
different bug in a different project is not worth the line. [[phronix-skill-authoring]]
`R0c` has the measured case: a skill carrying the exact correct code was read by
a weaker model, which reproduced the message string verbatim and still wrote
`assert` instead of `raise ValueError`, scoring 0/2.

### I6 — Attach it so it will be found

The skill is only worth writing if a later task retrieves it. Give it the
subject it belongs to rather than the instance id: the next task on this
repository has a different instance id and the same problem shape.

Call `graph_ensure` after writing so the links exist, and record the pipeline
with `research_record_pipeline` / `research_adopt_pipeline` so the pipeline is
data and not only prose.

## Rules

### R0 — A skill that solves a problem must say how to solve it

[[phronix-skill-authoring]] `R0` is the rule and carries the evidence, and `R0b` is its companion: every label you cite must resolve — a bare `X15` means a section of THIS skill, and a research record's approach identifier is not one. It bears
repeating here because this stage is where solution skills are born: the
`## Instructions` must contain the steps that fix the problem — file, function,
line, and what to change it to.

Measured: the skill written for `pallets__flask-4045` held the complete correct
answer inside 7,433 characters of Rules and References with an EMPTY
Instructions section, and cited an `I1` that did not exist. The model handed it
scored 0/2; the same task from scratch scored 1/2 on its first try.

Read it back before you finish: could someone fix this from the Instructions
alone?

### R1 — Why this stage has no clock

Every other stage in the pipeline is bounded, because exploration will consume
whatever it is given. This one cannot run away in the same manner: its input is
fixed, it is forbidden from exploring, and what it produces is exactly as large
as the findings it was handed.

And it is the only stage whose output survives the task. The attempt is thrown
away, the worktrees are thrown away, the findings are superseded — the tools and
the skill are what the next task starts from.

### Using the tools (capability)

- Render the procedure with `phronix_build_solution_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `problem`, `steps`, `tools_built`, `judgement`, `failed_directions`, `corner_cases`, `unresolved_labels`, `unverified`, `attached_subject`, `graph_ensured`, `pipeline_recorded`) to `phronix_build_solution_check`; a step is done only when the check passes.

## References

### X1 — Do not explore here

The exploring is over. If the findings are thin, build the solution the thin
findings support and say plainly what is unverified — do not spend this stage
going back to the repository to top them up. An unbounded stage that starts
investigating never ends.

## Constraints

- No exploring in this stage: no going back to the repository to top up thin findings (X1).
- No time limit: a solution cut off half-written wastes every minute the pipeline spent (R1).
- Name each tool for the question it answers, not the command it runs (I2).

## Corner cases

- An attempt that implemented an idea badly tells you about the implementation, not the idea: 'dot validation does not work', written once, rules the correct answer out of every future task on the repository (I4).
- A skill that opens with 'research on flask' is retrieved for the wrong bug; say what you solved so no matching heuristic has to guess (I5).
- Anything you write that would still be true of a different bug in a different project is not worth the line (I5b).
- The test a CORRECT fix breaks must be named, so the reader does not undo their own right answer (I5b).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_build_solution_plan`, validator `phronix_build_solution_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `problem_symptom` failed: open with the symptom: what was observed to be wrong (I5)
- `problem_case` failed: name the failing test or the smallest input that shows it (I5)
- `problem_cause` failed: say where in the code the behaviour comes from (I5)
- `instructions_not_empty` failed: the Instructions must hold the steps that fix the problem: file, function, line, what to change it to (R0)
- `steps_checkable` failed: each step is one thing done with a way to tell whether it worked (I1)
- `deterministic_steps_are_tools` failed: build the deterministic step as an MCP tool with capability_new and name it in the step (I2)
- `failures_not_abandonments` failed: say what failed (where it was implemented and what it missed), not what to abandon (I4)
- `corner_cases_listed` failed: list per step what a smaller model would write instead and why it fails (I5b)
- `labels_resolve` failed: every label cited must be a section of this skill; a research approach id is not one (R0, R0b)
- `attached_by_subject` failed: attach to the subject the problem belongs to, not the instance id (I6)
- `graph_linked` failed: call graph_ensure after writing (I6)
- `pipeline_recorded` failed: record the pipeline with research_record_pipeline / research_adopt_pipeline (I6)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A solution skill is later found with an empty Instructions section or unresolvable labels: rewrite it per R0 before anything retrieves it again.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- Every deterministic step of the solution is a new capability (capability_new); only the judgement stays in the skill.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Symptom/case/cause opening, then ordered checkable steps with tools for the deterministic ones, corner cases from the trials, graph_ensure + research_record_pipeline (phronix-build-solution, 2026-09-15).
- `phronix_build_solution_plan` -> follow the checklist -> `phronix_build_solution_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
