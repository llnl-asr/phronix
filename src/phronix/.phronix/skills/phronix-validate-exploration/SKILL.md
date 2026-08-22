---
name: phronix-validate-exploration
description: Judge whether the explored ideas actually answered their questions — name the ones that came back thin or unattempted so they can be explored again, and let the rest through.
subject: judge whether the explored ideas actually answered their questions
type: skill
---


# Validating what the exploring found

Each idea was explored under a clock, and a stage that runs out of time files
what it had. Some of those findings answer their question and some do not. You
decide which, and you have no budget — you are reading findings, not making
them.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | A finding is complete when it answers its own question |
| `I2` | Instructions | Name what needs another pass, and why |
| `I3` | Instructions | A negative result is complete |
| `I4` | Instructions | Let it through when it is good enough |
| `X1` | References | Do not fill the gap yourself |
| `X2` | References | Do not write the fix |
| `R1` | Rules | Why this exists at all |

## Instructions

### I1 — A finding is complete when it answers its own question

Ask of each one:

* Was the idea actually **tried**, or only reasoned about? A finding with no
  evidence of running anything is a hypothesis wearing a finding's clothes.
* Does it say what **happened**, in numbers where there are numbers?
* Does it say what that **rules in and out**? A result nobody drew a conclusion
  from leaves the conclusion to the build stage, which has less context.
* Was it cut off? A finding that stops mid-measurement is explicitly partial and
  is the clearest case for another pass.

### I2 — Name what needs another pass, and why

For each idea that failed the check, say which of the above is missing. "Thin"
is not actionable; "tried the absolute form only, never the relative one, which
is the case the issue reports" tells the next pass exactly what to do.

An idea sent back is explored again with your reason attached, so the second
pass is not a repeat of the first.

### I3 — A negative result is complete

**An idea that was tried and did not work is finished.** It answered its
question. Sending it back because the answer was disappointing wastes a pass and
risks the second attempt manufacturing a positive result to satisfy you.

The same goes for an idea that turned out to be irrelevant: "this is not where
the problem is" is a real answer and it narrows the solution.

### I4 — Let it through when it is good enough

Every pass costs the wall clock that the budgets exist to bound. If the findings
between them let the solution be built, say so and stop — the build stage can
work from partial evidence and is required to mark what is unverified.

Send back only what would change the solution.

## Rules

### R1 — Why this exists at all

The explore stage is a prediction: that two minutes is enough to answer the
question. Sometimes it is not, and before this check the pipeline could not tell
the difference between "explored and answered" and "explored and ran out" — both
arrived as a filed finding, and the solution was built as if they were the same
thing.

## References

### X1 — Do not fill the gap yourself

If a finding is missing its measurement, do not go and take the measurement.
That is exploring, it is budgeted, and doing it here hides the cost in a stage
that reports none. Name the gap and let the explorer close it.

### X2 — Do not write the fix

**No patches, no diffs, no code.** You have no editing tools, and writing a
patch as text does not become one — it is output nobody applies, produced by a
stage with no clock, while the actual verdict goes unrecorded.

Measured: thirty-five `*** Begin Patch *** Update File: ...` blocks from a
single validation pass. The model could not edit, so it narrated edits instead.

If you find yourself reaching for a patch, that is the signal the finding is
already complete enough to build from. Record that it is complete and stop.
