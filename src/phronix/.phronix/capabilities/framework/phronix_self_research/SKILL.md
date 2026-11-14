---
name: phronix_self_research
description: Research an unfamiliar task before attempting it: gate on catalogue coverage (research_assess covered/gap), fix a measurable figure of merit first, characterise the problem kind, look it up externally before reading code, ground findings in this checkout, measure at least two rival approaches on train/validate/unseen-test instances, split the plan into deterministic (capability) and judgement (skill) steps, verify and record achieved. Load at the start of any task the library does not already cover, or when research_choose returns inconclusive or research_verify fails 'evidence'/'constraints'.
---
Cross-references: [[knowledge]], [[capability_builder]], [[phronix_research_plan]], [[phronix_research_as_tools]], [[phronix_verification]], [[phronix_build_solution]]

# Self-research: how a task should be done, before doing it

Converted from the dftracer-agents skill `phronix-self-research` (subject: researching how a task should be done before doing it). Source description: How to work out the way an unfamiliar task should be done before attempting it: gating on catalogue coverage, fixing a figure of merit in advance, measuring rival approaches, and turning the winner into capabilities and skills. Load at the start of any task the library does not already cover.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** Partial: capability_builder ('knowledge_search first', deterministic steps -> capability) covers I1 and R4 in general form; the research_* method (FoM, phases, rivals) has no store equivalent.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Gate on catalogue coverage before researching anything |
| `I2` | Instructions | Declare the figure of merit before looking at approaches |
| `I3` | Instructions | Characterise the subject before searching for it |
| `I4` | Instructions | Look it up externally before reading the code |
| `I5` | Instructions | For a tool, learn its surface: commands, flags, semantics |
| `I6` | Instructions | Ground the external findings in this codebase |
| `I7` | Instructions | Find rival approaches and measure them |
| `I10` | Instructions | Build task instances: train, validate, test |
| `I11` | Instructions | Tune on validate, confirm on unseen, then write it up |
| `I8` | Instructions | Split the plan into deterministic and judgement steps |
| `I9` | Instructions | Verify the research, then record what was achieved |
| `R1` | Rules | Never compare approaches before the figure of merit exists |
| `R2` | Rules | A figure of merit must state how it is measured |
| `R3` | Rules | Record rejected approaches with their numbers |
| `R4` | Rules | Deterministic steps become capabilities, never prose |
| `R5` | Rules | Repeated failure in one location is evidence to look elsewhere |
| `R6` | Rules | Every approach records its source; at least one from outside |
| `R7` | Rules | Measure the figure of merit; a prediction cannot decide |
| `R8` | Rules | Only the unseen test instances confirm or falsify |
| `R9` | Rules | Keep unconfirmed approaches as backups; never rediscover them |

## Instructions

### I1 — Gate on catalogue coverage before researching anything

Call `research_assess(task=...)` first. It counts matching blocks in the skill
catalogue and returns `covered` or `gap`.

On `covered`, load the named skills and proceed — a second parallel account of a
subject already documented will contradict the first within a few sessions. On
`gap`, research before attempting.

Do not substitute your own sense of familiarity for this check. It is
deterministic precisely because confidence is the wrong signal here.

### I2 — Declare the figure of merit before looking at approaches

`research_define_fom(topic, name, direction, target, measure)` fixes the single
number that decides, which direction is better, the threshold to reach, and how
the number is obtained.

Prefer a number the task is already judged on over one you invent. For a bug fix
that is usually target tests passing, with regressions as a constraint.

### I3 — Characterise the subject before searching for it

Name what kind of problem this is before looking anything up, because it decides
where to look:

- **a bug in a library** — the project's own issue tracker, commits and changelog
  usually contain the fix or the discussion that leads to it;
- **using a tool** — its documentation and `--help`; the failure is normally a
  flag or a semantic you have not read yet, not a defect;
- **an algorithm or format** — the specification, then a reference
  implementation;
- **an environment or build problem** — release notes and the version in play.

Write the characterisation down in the approach summaries. A search performed
without knowing which of these it is returns the wrong kind of answer
confidently.

### I4 — Look it up externally before reading the code

Do this *first*, before mapping the local code paths. Reading the code first
anchors you to the file you happen to open, and every later search becomes a
search for confirmation.

For a known bug, the sequence that pays: the issue as filed, then whether it was
ever fixed upstream, then the commit that fixed it and what it touched. That
routinely names the exact function and turns the whole task into applying a known
change — which is the correct outcome, not a shortcut.

Use `WebSearch` for the general question and `WebFetch` for the specific page.
Record what you find with `research_add_approach(..., source=<url or reference>)`.

### I5 — For a tool, learn its surface: commands, flags, semantics

When the subject is a tool rather than a defect, spend the search budget on what
the tool actually offers:

- run its `--help` and the `--help` of the relevant subcommand;
- read the documentation for the exact option in play, including its default and
  what it interacts with;
- find how the same task was accomplished elsewhere — a worked example beats a
  parameter list, because it shows the combination that works.

Record the commands and options you confirmed. A tool's surface is durable
knowledge: it is worth a skill block, and the next task on the same tool should
not have to rediscover it.

### I6 — Ground the external findings in this codebase

Only now map the code. For each candidate the external search produced, locate
the code path it refers to in *this* checkout and at *this* version, and confirm
the code actually looks the way the source implies. Upstream moves; a fix
described against a later version may not apply here.

An external finding you could not locate in the code is not a rejected
approach — record it with what you looked for and why it did not match, so the
next session does not repeat the search.

### I7 — Find rival approaches and measure them

At least two genuinely different approaches, each recorded with
`research_add_approach` and whatever you measured.

Look past the first suspect file: upstream issues and commits via `WebSearch` and
`WebFetch`, every code path that could produce the behaviour via `Grep` and
`Read`, and actual runs via `Bash`. A measurement beats an argument.

### I10 — Build task instances: train, validate, test

Author small, cheap cases that exhibit the behaviour — a reproducer script, an
input with a known result — with `research_add_instance`, and assign each a
phase:

- **train** — discovery. These are how you work out what governs the behaviour
  and which approaches exist at all. Failing them means nothing.
- **validate** — refinement. Tune approaches against these and compare them.
  Rework as often as needed; that is the phase's purpose.
- **test** — correctness, on cases no approach was shaped against.

Write the test instances *before* you begin tuning, and do not consult them
while you work. An unseen set you looked at is a tuning set.

### I11 — Tune on validate, confirm on unseen, then write it up

Record every trial with `research_record_trial`, failures included, then call
`research_evaluate_approach`. It sets the status deterministically:

`confirmed` requires passing validate **and** the unseen test instances, and is
the only status that licenses writing the approach up as a skill.

An approach that passes validation and nothing else has demonstrated that it can
be tuned, which is not the claim being made.

### I8 — Split the plan into deterministic and judgement steps

`research_write_plan(topic, steps)` with each step tagged `deterministic` or
`judgement`. Build the deterministic ones with `capability_new` before the plan
is used; write the judgement ones as skill blocks.

Most steps that feel like judgement are not. "Run the failing test and read the
assertion" is mechanical. "Decide which layer should normalise the path" is not.

### I9 — Verify the research, then record what was achieved

`research_verify(topic)` before acting on the plan, and again after executing it
once `research_record_achieved(topic, value)` has recorded the delivered figure
of merit.

The gap between an approach's predicted number and the achieved one is the most
useful thing this loop reports.

## Rules

### R1 — Never compare approaches before the figure of merit exists

`research_choose` refuses without one. A criterion chosen after the results are
in is a justification for the approach already preferred, not a test of it — and
the resulting record reads exactly like a rigorous comparison.

### R2 — A figure of merit must state how it is measured

A number nobody can re-derive cannot be checked by a corrector. An unfalsifiable
criterion is worse than none, because it lends the appearance of rigour to a
choice that was never measured.

### R7 — Measure the figure of merit; a prediction cannot decide

`research_choose` returns `inconclusive` when no approach measured the figure of
merit, and the corrector fails `constraints` when the winner's value was
predicted.

An argmax over predicted numbers returns whichever approach the agent already
believed in, dressed as a comparison. Apply the candidate, run the measurement
the figure of merit names, and pass it as `measurement=`.

### R8 — Only the unseen test instances confirm or falsify

Failing `train` or `validate` does not refute an approach — those phases exist
for discovery and tuning, and discarding a candidate for failing them throws
away work that only needed another iteration.

Failing `test` does refute it, permanently. That set was never used to shape the
approach, which is the entire reason its verdict counts.

### R9 — Keep unconfirmed approaches as backups; never rediscover them

An approach that is neither confirmed nor falsified stays on record with its
trials. `research_backups` returns them best-first, and a retry starts there.

Research that begins again from nothing after each failed attempt pays full
price to rederive the same set of ideas, and usually arrives at whichever one it
thought of first the last time.

### R3 — Record rejected approaches with their numbers

An approach dismissed without a measurement will be tried again by the next
session. A rejected approach carrying a poor measured result is what stops it.

### R4 — Deterministic steps become capabilities, never prose

A mechanical procedure written as prose is a procedure that will be performed
differently next time. If the step has one right answer for given inputs, it is
code — `capability_new` — not a paragraph.

### R6 — Every approach records its source; at least one from outside

`research_verify` fails the `evidence` facet when no approach says where it came
from, or when every approach came from reading the local checkout.

An unsourced approach cannot be checked and will be re-invented by the next
session. A set of approaches sourced entirely from the file in front of you is
not research; it is the same guess written down several ways, and it reads
identically to genuine investigation once it is in the record.

### R5 — Repeated failure in one location is evidence to look elsewhere

When several attempts have changed the same file and the target still fails, the
useful thing to record is the exclusion: *the cause is not here*. Knowledge that
only ever accumulates about the area already being tried makes the next attempt
more confident and no more correct.

### Using the tools (capability)

- Render the procedure with `phronix_self_research_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `coverage`, `fom`, `kind`, `approaches`, `instances`, `chosen`, `plan_steps`) to `phronix_self_research_check`; a step is done only when the check passes.

## References

## Constraints

- No comparison before the figure of merit exists (R1).
- Never consult test instances while tuning (I10).
- Never write up an approach that is not confirmed (I11).
- Never discard an approach for failing train or validate (R8).

## Corner cases

- A fix described upstream against a later version may not apply here: ground it in this checkout (I6).
- An external finding you could not locate is not a rejected approach: record what you looked for (I6).
- Most steps that feel like judgement are not: 'run the failing test and read the assertion' is mechanical; 'decide which layer should normalise the path' is not (I8).
- An approach that passes validation and nothing else has only shown it can be tuned (I11).
- Approaches sourced entirely from the file in front of you are the same guess written several ways (R6).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_self_research_plan`, validator `phronix_self_research_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `coverage_assessed` failed: call research_assess first (I1)
- `fom_measure` failed: research_define_fom with how the number is measured, before comparing (I2, R1, R2)
- `kind_characterised` failed: characterise the subject before searching (I3)
- `two_approaches` failed: record at least two genuinely different approaches (I7)
- `approaches_sourced` failed: every approach records where it came from (R6)
- `external_source` failed: at least one approach must come from outside the checkout: issue, upstream commit, docs (I4, R6)
- `rejected_have_numbers` failed: record a rejected approach with its measured number (R3)
- `unseen_test_set` failed: write test instances before tuning, and never consult them while tuning (I10)
- `chosen_confirmed` failed: only 'confirmed' (passing validate AND unseen test) licenses writing it up; keep others as backups (I11, R8, R9)
- `chosen_measured` failed: apply the candidate and pass the real measurement=; a predicted value cannot decide (R7)
- `plan_tagged` failed: tag every plan step deterministic or judgement and build the deterministic ones as capabilities (I8, R4)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- research_verify fails 'evidence': add an external source; fails 'constraints': replace the predicted winner value with a measurement.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A tool's confirmed surface (commands, options, defaults) becomes a tools_<x> capability; the confirmed approach becomes a solution skill with its deterministic steps as capabilities.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- For a known bug: the issue as filed -> fixed upstream? -> the fixing commit names the function; applying a known change is the correct outcome (phronix-self-research I4, 2026-09-15).
- `phronix_self_research_plan` -> follow the checklist -> `phronix_self_research_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
