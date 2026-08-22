---
name: phronix-validate-ideas
description: Judge whether a plan's ideas are worth exploring — keep the ones that could actually change the outcome, drop the rest, and say plainly how many good ones remain.
subject: judge whether a plan's ideas are worth exploring
type: skill
---


# Validating the ideas a plan produced

The plan is a prediction: that these are the questions worth two minutes each.
You are the corrector. Your job is to say which of them are actually worth it,
and you have no budget — this is reading and judging, not investigating.

Three good ideas is the target. Fewer means the plan runs again.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What makes an idea good |
| `I2` | Instructions | What to do with a bad one |
| `I3` | Instructions | Three, and say the number |
| `X1` | References | Judge from what you were given, and stop |
| `X2` | References | Do not explore, and do not solve |
| `R1` | Rules | Why the corrector is unbudgeted and the predictor is not |

## Instructions

### I1 — What makes an idea good

**It could change what we do.** An idea whose answer leads to the same patch
either way is not worth exploring. "Which file is this in" is usually already
known or trivially found; "does the fix have to handle the relative form too"
changes the patch.

**It is answerable in two minutes by trying something.** An idea that needs the
whole test suite run, or a survey of the library's history, will come back
empty and the slot is wasted.

**It is independent of the others.** They are explored in parallel, so an idea
that only makes sense after another's answer will be explored with the wrong
input.

**It is not already settled.** If the store or the task description answers it,
exploring it spends a slot re-deriving a known answer.

### I2 — What to do with a bad one

Drop it, and say why in one line. Do not rewrite it into a different idea —
that is the plan's job, and the plan gets another turn if you leave it short.

Record the surviving ideas with `research_set_aspects`, in priority order. The
list you write IS the list that gets explored, so an idea you leave in is one
you are committing two minutes to.

### I3 — Three, and say the number

End by stating how many good ideas remain. If it is fewer than three, the plan
stage runs again and is told what you rejected, so name the rejections
specifically enough that the next plan does not simply repeat them.

Do not pad to three. Two good ideas and an honest count beats three where the
third is filler — filler is explored at the same cost as substance, and its
finding then dilutes the solution.

## Rules

### R1 — Why the corrector is unbudgeted and the predictor is not

Generating ideas is open-ended: an agent will read the whole repository looking
for one, so it gets a clock. Judging a list of three is bounded by the list —
there is nothing to run away into. Putting a clock on it would only ever cut
the cheap half of the loop.

## References

### X1 — Judge from what you were given, and stop

You have the ideas and the record. That is enough to say which are worth two
minutes, and it is nearly all you should look at.

A lookup or two is fine — the task's own record, a skill that plainly covers
this problem. Wandering is not: listing every skill, recalling every memory,
loading three skills in turn, reaching for a probe. Measured, a validation pass
did exactly that for fifteen minutes and was killed before it recorded
anything, having judged nothing at all.

**If you have read enough to have an opinion, record it and finish.** An
unrecorded judgement is worth less than a quick one.

### X2 — Do not explore, and do not solve

You are judging the questions, not answering them. If you find yourself opening
files to decide whether an idea is good, the idea is probably fine and you are
doing the next stage's work at its expense.
