---
name: phronix-stage-finalize
description: How to close out a research stage that ran out of time — record what it already established so the next stage has its input, and explore nothing further.
subject: close out a research stage that ran out of time
type: skill
---


# Producing a stage's result from what it did

A stage of the research pipeline has stopped. Its thinking is not lost: it is in
the transcript above. What is missing is the *filing* — the tool call that turns
what it found into a record the next stage can read.

Your whole job is that filing, and there is no clock on it. The handoff has to
be complete, and a half-written record is worse than a slow one.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Record, do not investigate |
| `I2` | Instructions | File to the phase you were in |
| `I3` | Instructions | Partial is the expected outcome |
| `R1` | Rules | Why this is a corrector, not a rescue |
| `X1` | References | Not for a stage that failed |

## Instructions

### I1 — Record, do not investigate

Do not read files, run commands, or search. Not because they are slow — nothing
here is rushed — but because they are not yours to do. The stage's findings are
what they are; anything you looked up now would be a finding nobody measured,
entering the record as though the stage had established it.

Read what the stage said. Call the recording tool for its phase. Stop.

If the stage genuinely established nothing, record nothing and say so in one
line. An invented aspect or a guessed approach is worse than an absent one:
the next stage cannot tell it from a real finding, and will spend its own
budget pursuing it.

### I2 — File to the phase you were in

The stage name tells you which record is owed:

| stage | what it owes |
|-------|--------------|
| `plan` | `research_set_aspects` — the angles worth investigating |
| `aspect` / `aspect-record` | the finding for that one aspect |
| `collect` | the reconciliation across aspects |
| `propose` | `research_add_approach` for each candidate named |
| `tune` | `research_record_trial` for every measurement taken |
| `evaluate` | `research_evaluate_approach` for what was scored |
| `diagnose` | the diagnosis, and what it rules out |

A stage that named three approaches in prose and filed none should file three.
That is the common case and the reason this exists.

### I3 — Partial is the expected outcome

Record what exists, including the incomplete parts, and mark them as partial
rather than rounding them up. A trial with two of five instances measured is a
trial with two instances measured — the ranking that reads it can weigh a thin
measurement correctly, but only if it knows the measurement is thin.

Never fabricate the rest to make a record look complete.

## Rules

### R1 — Why this is a corrector, not a rescue

The budget is the prediction that a stage's work fits in its time. This is the
corrector: it makes the prediction safe to be wrong about, by guaranteeing the
next stage still receives an input.

Which is what lets budgets be *tight*. A stage that must either finish or lose
everything has to be given enough time for its worst case; a stage whose
findings are filed either way can be given enough for its typical one, because
overrunning costs a filing pass rather than the whole pipeline.

This only holds if the filing itself always completes, which is why it is the
one step in the pipeline with no ceiling. A capped finalize was measured being
killed mid-handoff, and a corrector that fails takes the prediction down with
it.

## References

### X1 — Not for a stage that failed

If the stage errored, crashed, or never started, there is nothing to file.
Say so and return. This skill records work that happened, and a stage that
produced no thinking produced no findings to record.
