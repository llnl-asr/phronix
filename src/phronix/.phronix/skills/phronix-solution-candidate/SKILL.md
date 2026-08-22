---
name: phronix-solution-candidate
description: Write the solution skill for ONE researched approach, so that rival approaches can be tried against the real tests and compared fairly — steps a stranger can execute, not an account of the reasoning.
subject: turning one researched approach into an executable solution skill
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Write steps, not the story |
| `I2` | Instructions | A tool per step wherever one exists |
| `I3` | Instructions | Every step carries its own check |
| `R1` | Rules | Give your approach its fairest statement |
| `R2` | Rules | Short, because every block is read forever |
| `R3` | Rules | Yours is kept and linked, whatever the outcome |
| `X1` | References | Why the write-ups are written in parallel |

## Instructions

### I1 — Write steps, not the story

An agent that has never seen this task will be handed your skill and nothing else, and must produce the fix from it. It cannot ask you what you meant.

So write what to *do*, in order. Not what you concluded, not why the approach is promising, not what you ruled out — those belong in the research record, and this skill is the part someone executes.

### I2 — A tool per step wherever one exists

Name the tool and its arguments. A step that says "check whether the path is normalised" is a step the reader has to design; `probe_ignore_paths_matrix(path=...)` is one they can run.

Where no tool fits, write one instruction a reader can follow without inferring anything. If you find yourself writing "investigate whether", that is research leaking into a solution — decide it now, or build the tool that decides it.

### I3 — Every step carries its own check

Say what proves the step worked. A failure then surfaces at the step that caused it, rather than at the end where everything looks equally suspect.

This is what makes a losing approach useful: a skill that fails at step 2 with a clear check tells you the approach is wrong; one that fails at the end tells you nothing.

## Rules

### R1 — Give your approach its fairest statement

Other agents are writing the skills for the rival approaches at the same time, and all of them will be tried against the real tests. Do not hedge toward the others or soften a claim you believe.

A strong idea losing to a weak write-up corrupts the comparison, and the comparison is the point: it is the only thing that tests whether the research metric ranked them correctly.

If your approach turns out to be wrong, that is a result. Say so plainly rather than quietly widening the skill until it covers someone else's idea.

### R2 — Short, because every block is read forever

Every block is read on every future retrieval of this skill. A step nobody can act on costs context on every task that loads it.

Lead with the action. One idea per block. Split rather than combine.

### R3 — Yours is kept and linked, whatever the outcome

Your skill is not scaffolding to be thrown away when the trials are scored. When
every candidate has been tried, the subject's own skill is merged out of them
and links back to each one — including the ones that lost.

So write it to stand on its own. A reader who follows that link is asking "was
this tried, and what happened?", and the answer has to be here rather than
restated in the merged skill. That is what makes a losing candidate worth
keeping: an idea recorded with the check that killed it costs the next task a
sentence, and an unrecorded one costs it an attempt.

## References

### X1 — Why the write-ups are written in parallel

Research ranks approaches against a figure of merit measured on a corpus it built itself — a proxy. The top-ranked approach is the most promising one, not the correct one.

Trying several against the task's own tests is what settles it, and that is affordable because the attempts are independent: N approaches cost wall clock once rather than N times. What it requires is that each approach arrive as its own skill, which is this skill's job.
