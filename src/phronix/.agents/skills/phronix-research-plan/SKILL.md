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

## I1. Three records, in this order

**The metric.** `research_define_fom(...)` — the number that decides which
approach is better, derived from THIS task, with `measure` stating exactly how
it is obtained. Fixed before any approach exists, because a figure of merit
chosen after the candidates is a figure of merit chosen to pick one.

**The dataset.** `research_declare_corpus(...)` with the axes along which cases
differ here, then `research_add_instances(...)` and `research_split(...)`.

**The aspects.** `research_set_aspects(...)` — the independent questions to
investigate, in priority order. Each must be answerable without waiting on the
others, because they are investigated in parallel.

## I2. At least twenty instances, genuinely diverse

Twenty is not arbitrary: the split holds back 20% as the unseen set, so a corpus
of ten decides everything on two cases, and two cases can be passed by accident.

They must be spread across the axes just declared, not twenty spellings of one
case. A corpus that varies in one dimension measures that dimension and reports
it as correctness. Cover the boring directions: the relative form as well as the
absolute, the nested case as well as the top level, the one that should NOT
match as well as the one that should.

**Negative cases matter most**, because a change that ignores everything passes
every positive case there is.

## I3. Add the instances in the same breath as the axes

This is the step that most often does not happen. Declaring the axes is quick
and satisfying; then the instances never get written, the measuring stage has
nothing to measure against, and it spends its budget discovering that.

Call `research_split` before you finish.

## I4. Plan around what is already known

Call `research_prior(question=...)` for what the store holds on this subject.

An aspect the record already settles will be re-checked rather than
re-investigated, which is cheap — so it costs nothing to list it, and listing it
is how the re-check happens. But do not spend a NEW aspect on covered ground:
aspects are the expensive stage, only a few run, and one spent re-deriving a
known answer is one not spent on the part nobody has looked at.

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
