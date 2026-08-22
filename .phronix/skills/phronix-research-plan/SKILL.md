---
name: phronix-research-plan
description: How to plan a research pass — work out what the task is, fix the metric that will decide between approaches, build the corpus to measure on, and name the independent aspects to investigate in parallel.
---

# Planning a research pass

This is the first stage, and it decides how the question gets answered — not
what the answer is. Do not edit anything and do not fix anything.

It also absorbs what used to be a separate survey: reading the issue and asking
what the store already knows are both part of working out what the task *is*,
and neither needs a stage of its own.

## I1. First, summarise the problem from the artifact

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

## I2. Three records, in this order

**The metric.** `research_define_fom(...)` — the number that decides which
approach is better, derived from THIS task, with `measure` stating exactly how
it is obtained. Fixed before any approach exists, because a figure of merit
chosen after the candidates is a figure of merit chosen to pick one.

**The dataset.** `research_declare_corpus(...)` with the axes along which cases
differ here, then `research_add_instances(...)` and `research_split(...)`.

**The aspects.** `research_set_aspects(...)` — the independent questions to
investigate, in priority order. Each must be answerable without waiting on the
others, because they are investigated in parallel.

## I3. At least twenty instances, genuinely diverse

Twenty is not arbitrary: the split holds back 20% as the unseen set, so a corpus
of ten decides everything on two cases, and two cases can be passed by accident.

They must be spread across the axes just declared, not twenty spellings of one
case. A corpus that varies in one dimension measures that dimension and reports
it as correctness. Cover the boring directions: the relative form as well as the
absolute, the nested case as well as the top level, the one that should NOT
match as well as the one that should.

**Negative cases matter most**, because a change that ignores everything passes
every positive case there is.

## I4. Add the instances in the same breath as the axes

This is the step that most often does not happen. Declaring the axes is quick
and satisfying; then the instances never get written, the measuring stage has
nothing to measure against, and it spends its budget discovering that.

Call `research_split` before you finish.

## I5. Plan around what is already known

Call `research_prior(question=...)` for what the store holds on this subject.

An aspect the record already settles will be re-checked rather than
re-investigated, which is cheap — so it costs nothing to list it, and listing it
is how the re-check happens. But do not spend a NEW aspect on covered ground:
aspects are the expensive stage, only a few run, and one spent re-deriving a
known answer is one not spent on the part nobody has looked at.

## I6. Finding an idea the existing ones do not cover

When you are asked for more ideas, you are given the ones already kept as a
single line each. That is deliberate: enough to see what is covered, not enough
to elaborate on. Elaborating is the trap — it produces a third idea that is the
first one reworded, which is filler and will be rejected.

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
system. If your third idea would be investigated by opening the same file as
the first, it is probably the first one again.

**Two good ideas and an honest count beats three where the third is padding.**
Say so if the angles are genuinely exhausted — but say it after trying the axes
above, not instead of trying them.

## X1. No approaches yet

Naming a candidate here commits the investigation to it before anything has been
looked at, and the aspects then go looking for evidence for that candidate
rather than for what is true.

## R1. Why the metric comes first

Everything downstream is arithmetic over recorded trials: tuning measures each
approach against the corpus, and the ranking reads those measurements. With no
metric and no corpus there is nothing for later stages to do but argue, and an
argument is not a measurement.

A stage stopped at its budget still files what it found. A plan with a metric
and a corpus and two aspects is worth more than a perfect plan that never got
recorded.
