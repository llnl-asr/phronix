---
name: phronix_research_plan
description: Plan a research pass: summarise the failed attempt from exchange.md first, fix the metric (research_define_fom) before any approach, declare a corpus of at least 20 diverse instances with negatives and split it, and record 3-6 independent STEPS as aspects, each with its own `where`. Load at the first stage of a research pass or a retry, and when research_set_aspects rejects a list (numbered candidates 'A1:', 'Option 2', or every aspect in the same file).
---
Cross-references: [[phronix_self_research]], [[phronix_explore_idea]], [[phronix_validate_ideas]], [[phronix_research_as_tools]], [[phronix_learn_from_attempt]]

# Planning a research pass

Converted from the dftracer-agents skill `phronix-research-plan` (subject: plan a research pass). Source description: How to plan a research pass — work out what the task is, fix the metric that will decide between approaches, build the corpus to measure on, and name the independent aspects to investigate in parallel.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

# Planning a research pass

This is the first stage, and it decides how the question gets answered — not
what the answer is. Do not edit anything and do not fix anything.

It also absorbs what used to be a separate survey: reading the issue and asking
what the store already knows are both part of working out what the task *is*,
and neither needs a stage of its own.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | First, summarise the problem from the artifact |
| `I2` | Instructions | Three records, in this order |
| `I3` | Instructions | At least twenty instances, genuinely diverse |
| `I4` | Instructions | Add the instances in the same breath as the axes |
| `I5` | Instructions | Plan around what is already known |
| `I5b` | Instructions | Decompose into STEPS, then find ways to do each step |
| `I6` | Instructions | Ideas must be INDEPENDENT, from the first list onward |
| `X1` | References | No approaches yet |
| `R1` | Rules | Why the metric comes first |
| `R2` | Rules | Ideas are appended, not replaced |
| `R3` | Rules | Three ideas is the floor, not the target |

## Instructions

### I1 — First, summarise the problem from the artifact

On a retry you are given `exchange.md`: the complete record of the attempt that
failed — what the agent was asked, what it said as it worked, what it changed,
and what the tests printed. It is evidence rather than background, and it is
raw on purpose.

**Summarise it before you plan, and record that summary.** Your reading of the
problem is the thing every later stage works from; a digest someone else wrote
would be their reading, and the harness that would have written it cannot tell
which half-sentence in a transcript is the clue.

Four things in it, each ruling something out:

* **the change that was tried**, as a diff — the previous reading of the
  problem, written down. An idea that would produce this diff again has already
  been measured and has already failed.
* **the target tests still failing** — precisely what "solved" means here
* **the pytest output** — what the code actually did, not what anyone expected
* **the agent's own account** — what it believed it was fixing, which is where
  the reading went wrong

Do this before anything else — before the metric, before the corpus, before any idea. Record the summary with `research_observe(what=..., stage="plan")` so the stages after you inherit your reading rather than re-deriving it.

Read the diff before you plan. A plan that does not account for it proposes the
failed change a second time, in different words, and spends the whole pass
rediscovering the same result.

If the diff is empty, the problem is not a wrong fix — nothing was edited, and
the plan's first job is to find out why the attempt could not act.

### I2 — Three records, in this order

**The metric.** `research_define_fom(...)` — the number that decides which
approach is better, derived from THIS task, with `measure` stating exactly how
it is obtained. Fixed before any approach exists, because a figure of merit
chosen after the candidates is a figure of merit chosen to pick one.

**The dataset.** `research_declare_corpus(...)` with the axes along which cases
differ here, then `research_add_instances(...)` and `research_split(...)`.

**The aspects.** `research_set_aspects(...)` — the independent questions to
investigate, in priority order. Each must be answerable without waiting on the
others, because they are investigated in parallel.

### I3 — At least twenty instances, genuinely diverse

Twenty is not arbitrary: the split holds back 20% as the unseen set, so a corpus
of ten decides everything on two cases, and two cases can be passed by accident.

They must be spread across the axes just declared, not twenty spellings of one
case. A corpus that varies in one dimension measures that dimension and reports
it as correctness. Cover the boring directions: the relative form as well as the
absolute, the nested case as well as the top level, the one that should NOT
match as well as the one that should.

**Negative cases matter most**, because a change that ignores everything passes
every positive case there is.

### I4 — Add the instances in the same breath as the axes

This is the step that most often does not happen. Declaring the axes is quick
and satisfying; then the instances never get written, the measuring stage has
nothing to measure against, and it spends its budget discovering that.

Call `research_split` before you finish.

### I5 — Plan around what is already known

Call `research_prior(question=...)` for what the store holds on this subject.

An aspect the record already settles will be re-checked rather than
re-investigated, which is cheap — so it costs nothing to list it, and listing it
is how the re-check happens. But do not spend a NEW aspect on covered ground:
aspects are the expensive stage, only a few run, and one spent re-deriving a
known answer is one not spent on the part nobody has looked at.

### I5b — Decompose the problem into STEPS, then find ways to do each step

**An idea is not a guess at the whole fix. It is one step of a method, and the
ways of doing that step are what you explore.**

Work out what would have to be true for the problem to be solved — the ordered
things that must happen — and record THOSE as the aspects. Each becomes a step
with its own `where`, and `research_add_approach(..., aspect="<step>")` attaches
the ways of doing it.

For `pylint a` failing when `a/a.py` sits in `a/` with no `__init__.py`:

```
WHOLE-FIX GUESSES (what this used to produce)
  module_resolution      "change how modules resolve"
  import_behavior        "change the import system"
  expand_modules         "change expand_modules.py"
  module-search-order    "change the search order"
        -> four names for one edit; each attempt all-or-nothing

STEPS (what the method should produce)
  1. decide whether `a` is a package, a namespace package, or a module
     where: pylint/lint/expand_modules.py
  2. compute the module name to report for a/a.py given that decision
     where: astroid modutils.modpath_from_file
  3. choose the sys.path root so the name resolves
     where: pylint/lint/expand_modules.py get_python_path
  4. keep the existing cases passing — a/ with __init__.py, a bare a.py
     where: tests/lint/unittest_lint.py
        -> each step is checkable on its own, and a wrong way at step 3 leaves
           steps 1, 2 and 4 standing
```

Why this is more robust, and it is the reason the change is worth the trouble:

* **A failure localises.** "The fix is in expand_modules.py" failing tells you
  nothing. "Step 3 chose the wrong root" tells you which step to redo and leaves
  the rest.
* **Steps compose; guesses do not.** One way per step assembles into a complete
  solution, and a second way for step 3 gives a second complete solution that
  differs in exactly one place. That is a real alternative — four rewrites of one
  function are not.
* **Coverage becomes checkable.** You can ask whether the steps together solve
  the problem. You cannot ask that of a bag of rival guesses.
* **The last step is usually "do not break what works".** Naming it stops a fix
  that passes the target test and breaks five others.

Three to six steps. Fewer means a step is really several; more means you are
writing the patch rather than the method. Each step needs a `where` — see `I6`,
which applies to steps exactly as it applied to ideas: two steps that would be
carried out in the same place are one step.

**`research_set_aspects` enforces this and will reject the list.** Two shapes
come back as an error rather than being recorded:

* **Numbered candidates.** `A1: Direct email with getattr() fallback`,
  `A2: Model method factoring`, `Option 2`, `Approach 3`. These are ways, and
  they belong on a step via `research_add_approach(..., aspect="<step>")`.
  Watch for this one specifically: `research_add_approach` hands back keys
  named `A1`, `A2`, `A3`, and it is easy to echo that shape into the step names
  by reflex. Measured on django-13551 — the record filled with `A1:`/`A2:`
  aspects, every count read healthy, and the method had never been decomposed.
* **Every step in the same place.** N aspects sharing one `where` are N ways of
  doing one step, by `I6`.

A step is named after **what has to become true**, not after how you would make
it true:

```
REJECTED (ways)                          ACCEPTED (steps)
  A1: direct email with getattr()          locate the inputs the token hashes
  A2: model method factoring               include the user's current email
  A3: conditional field introspection      keep tokens valid for users with none
                                           leave existing tokens' shape intact
```

Both lists are about the same bug. The left one is four rival edits to one
function; the right one is a method whose steps compose, and whose failures say
which step to redo.

### I6 — Ideas must be INDEPENDENT, from the first list onward

Two ideas are one idea when they would be investigated in the same place. This
is not a rule about wording — it is a rule about where you would have to look.

**State `where` for every idea, and make every `where` different.** The file, and
the function if you know it. `research_set_aspects` takes it, `explore` passes it
to whoever investigates, and it is checked: a list whose ideas name the same file
is sent back with the overlap named, however many ideas it has.

Measured on `pylint-dev__pylint-7114`. Four ideas were kept —
`module-name-conflict-resolution`, `init-file-fallback`, `module-search-order`,
`expand_modules` — and every one of them changed `get_python_path` in
`pylint/lint/expand_modules.py`. The super idea built from them rewrote the same
loop. Three tries, five containers each, every candidate scoring zero. Four names
for one reading of the problem.

**Move along an axis instead of along the wording.** Given two ideas, ask which
of these they *both* share, and change that one:

| axis | the move |
|------|----------|
| layer | they both look at the function; look at its caller, or its config |
| lifecycle | they both look at what is produced; look at what consumes it |
| direction | they both ask why the bad case fails; ask why the good case passes |
| polarity | they both test what should match; test what should NOT match |
| scope | they both look at this repository; look at what the library it wraps does |
| time | they both look at the code now; look at what changed and why |

A genuinely new idea usually feels like it is about a different part of the
system. **If your third idea would be investigated by opening the same file as
the first, it is the first one again** — rename it and it is still the first one.

The failing case tells you where to start, not where the cause is. When every
idea points at the function that raised, ask instead: who called it with that
argument, what decided the argument, what the test would need to be true, and
what a version that works does differently. Those live in different files, which
is the point.

**Two good ideas and an honest count beats three where the third is padding.**
Say so if the angles are genuinely exhausted — but say it after trying the axes
above, not instead of trying them.

## Rules

### R1 — Why the metric comes first

Everything downstream is arithmetic over recorded trials: tuning measures each
approach against the corpus, and the ranking reads those measurements. With no
metric and no corpus there is nothing for later stages to do but argue, and an
argument is not a measurement.

A stage stopped at its budget still files what it found. A plan with a metric
and a corpus and two aspects is worth more than a perfect plan that never got
recorded.

### Using the tools (capability)

- Render the procedure with `phronix_research_plan_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `summary`, `fom`, `axes`, `instances`, `split`, `prior_consulted`, `aspects`, `aspects_mode`) to `phronix_research_plan_check`; a step is done only when the check passes.

## References

### X1 — No approaches yet

Naming a candidate here commits the investigation to it before anything has been
looked at, and the aspects then go looking for evidence for that candidate
rather than for what is true.

### R2 — Ideas are appended, not replaced

Scouts are looking for ideas at the same time as you, on angles you were not
given, and they write to the same plan. Use `research_add_aspects`, which
appends; `research_set_aspects` replaces the list and would erase theirs.

Ideas that repeat one already recorded — by name or by question — are dropped
and named back to you. That is a request for a different axis, not a rejection
of the count.

### R3 — Three ideas is the floor, not the target

Record every distinct idea the failure supports.

Three is the number the pass needs to proceed, and treating it as the target is
how a plan ends up proposing exactly three and keeping two. Every idea that
survives validation is explored, written up as its own solution skill, and
tried against the task's real tests alongside the others — several attempts run
at once, so the fourth idea costs a slot, not a round.

An idea nobody proposed is the one that cannot win. A surplus one is judged and
discarded by the tests, which is what they are for.

## Constraints

- Do not edit anything and do not fix anything in the plan stage.
- The metric is fixed before any approach exists (I2, R1).
- Never research_set_aspects over scouts' ideas: append (R2).
- No approaches named in the plan (X1).

## Corner cases

- research_add_approach hands back keys named A1, A2, A3: easy to echo into step names by reflex; research_set_aspects rejects them (I5b).
- N aspects sharing one `where` are N ways of doing one step (I6); research_set_aspects sends the list back with the overlap named.
- The failing case tells you where to start, not where the cause is: ask who called it with that argument, what decided it, what a working version does differently (I6).
- Two good ideas and an honest count beats three where the third is padding, but only after trying the axes (I6).
- Ideas repeating a recorded one by name or question are dropped and named back: a request for a different axis (R2).
- Measured: a corpus of ten decides everything on two unseen cases, which can be passed by accident (I3).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_research_plan_plan`, validator `phronix_research_plan_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `summary_recorded` failed: summarise exchange.md (diff, failing tests, pytest output, the agent's account) and research_observe it before planning (I1)
- `fom_measured` failed: research_define_fom with `measure` stating exactly how the number is obtained, before any approach (I2, R1)
- `axes_declared` failed: research_declare_corpus with the axes cases differ along (I2)
- `twenty_instances` failed: add at least 20 instances in the same breath as the axes; ten decides everything on two unseen cases (I3, I4)
- `has_negatives` failed: add negative cases (should NOT match): a change that ignores everything passes every positive (I3)
- `split_done` failed: call research_split before you finish (I4)
- `prior_consulted` failed: research_prior(question=...) before choosing aspects (I5)
- `three_to_six_steps` failed: decompose into 3-6 steps; fewer means a step is really several (I5b, R3)
- `not_more_than_six` failed: more than six steps means writing the patch, not the method (I5b)
- `aspects_have_where` failed: give every step a `where` (file, and function if known) (I5b, I6)
- `steps_not_ways` failed: aspects are steps named for what must become true; numbered candidates are ways: attach them with research_add_approach(..., aspect=<step>) (I5b)
- `distinct_wheres` failed: two aspects with the same `where` are one idea: move one along an axis (layer, lifecycle, direction, polarity, scope, time) (I6)
- `appended` failed: use research_add_aspects (append); research_set_aspects would erase the scouts' ideas (R2)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- research_set_aspects rejected the list: rename ways into steps (what must become true) and give each a distinct `where`, then append.
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- A recurring decomposition for a problem shape (its steps and wheres) becomes a capability or a solution skill, not a note in the plan.
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- Steps not guesses for pylint `a/a.py` with no __init__.py: decide package kind (expand_modules.py), compute module name (astroid modpath_from_file), choose sys.path root (get_python_path), keep existing cases passing (unittest_lint.py) (phronix-research-plan I5b, 2026-09-15).
- `phronix_research_plan_plan` -> follow the checklist -> `phronix_research_plan_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
