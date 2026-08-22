---
name: phronix-learn-from-attempt
description: What to record after a task attempt — a solution file when it passed, lessons when it did not, and how to keep either short enough to be retrieved and acted on.
subject: what to record after a task attempt
type: skill
---


# Learning from one attempt

The attempt just finished. Your job is to record what it taught this system, so
the next session does not rediscover it. **Do not edit any source.**

Two files are your evidence:

- `attempt-diff.patch` — exactly what the agent changed.
- `attempt-notes.md` — the issue, the agent's own account, and **how it was
  judged**: which target tests still fail, which regressions it caused, and what
  earlier attempts already tried.

`exchange.md` is attached too when the attempt was evaluated: the whole
exchange, including **what the tests printed**. Read that, not only the verdict.
A verdict says *it did not pass*; the assertion and the traceback say *why*, and
only the second becomes a usable lesson.

Read them. The repository alone will not tell you what was investigated or why.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | It passed: write the solution, not just a lesson |
| `I2` | Instructions | Several candidates were tried: separate what worked from what did not |
| `I3` | Instructions | Say what failed, not what to abandon |
| `I4` | Instructions | Short, actionable entries — the constraint that matters most |
| `I5` | Instructions | Only record what the evidence supports |
| `I6` | Instructions | Name it for the subject |

## Instructions

### I1 — It passed: write the solution, not just a lesson

**A pass is the most valuable thing this system can record, and it was being
thrown away.** Every win so far came on the first attempt, where no research
runs — so nothing wrote down how the task was actually solved, and the next task
on that subject started from nothing.

When the verdict is resolved, the primary output is a **solution file**: the
skill for this subject, holding the pipeline that worked.

* the **problem it solved** — the symptom, the failing case, where the
  behaviour came from. A later agent reads this first to decide whether it has
  the same problem.
* the **steps that solved it**, in order, from the diff — not a narrative of the
  session. What to change, where, and how to tell it worked.
* the **evidence** — which target tests went from failing to passing.

If a skill for this subject already exists, **update it** rather than founding a
second one. Two skills for one subject split every later retrieval, and the
retrieval returns whichever fragment matched.

Build a `probe_` tool for any step that is deterministic — see
`phronix-research-as-tools`. A pipeline of tool calls survives; a paragraph
describing the same steps has to be re-derived.

### I2 — Several candidates were tried: separate what worked from what did not

From the second try onward, more than one approach may have been attempted
against the real tests. Record them as two different things in the same skill:

| passed | **approaches that work for this task** — with what they have in common, which is the fix |
| failed | **lessons learned** — what was tried, and what the tests printed when it ran |

Both go in the SAME skill for the subject — one file that says what works here
and what has already been ruled out. Two files split every later retrieval, and
a lesson kept apart from the solution is a lesson nobody reads while solving.

Where two passing candidates change the same thing in the same direction, that
is the answer and it is confirmed twice. Say so: a later task should be able to
tell "this worked once" from "several readings converged on this".

### I3 — Say what failed, not what to abandon

An attempt that implemented an idea badly has told you about the implementation,
not the idea. Write *"the check was added to `Blueprint.__init__` and did not
fire for the path the test uses"* — never *"dot validation does not work"*.

Measured: research found the accepted fix for a task, the attempt implemented it
poorly, and the store recorded the approach as refuted. Every later task on that
repository then started with the right answer ruled out.

### I4 — Short, actionable entries — the constraint that matters most

* A rule or instruction is at most a few sentences and states a **directive**:
  what to do or not do, and where. Not a plan, not a checklist, not a debugging
  walkthrough. If you are writing "Step 1… Step 2… investigate whether…", you
  are writing a research note, and whoever retrieves it must redo your
  reasoning to extract the point.
* One idea per block. Split rather than combine.
* Lead with the directive, then one line of why.

Measured: a run wrote a 12 KB skill whose buried third bullet contained the
correct fix. Three later attempts retrieved that skill and none acted on it.
Length destroyed it.

### I5 — Only record what the evidence supports

If you verified it — the test output shows it, the diff shows it — state it
plainly. If you are inferring, write it as `Hypothesis:` and say what would
confirm it. **Never write a guess as a Rule.** A run recorded "this test does
not exist, it is a placeholder name" as fact; the test existed, and the claim
became a lesson every later attempt inherited.

### I6 — Name it for the subject

`sympy-units-dimensions`, not `fix-issue-24066`. A skill named for one instance
is never retrieved again — the next task has a different instance id and the
same problem shape.

Finish by stating which calls you made. If you genuinely learned nothing
reusable, say so and why — but that is rare after a real debugging session, and
never true after one that passed.
