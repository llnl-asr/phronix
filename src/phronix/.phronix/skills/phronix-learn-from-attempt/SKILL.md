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
| `I7` | Instructions | A solved task owes the next run a skill it can LOOK UP |
| `I8` | Instructions | A partial pass is evidence in both directions |
| `I9` | Instructions | Memory is this session; a skill is what survives it |

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


### I7 — A solved task owes the next run a skill it can LOOK UP

`best_skill_for` does not search. Before an attempt starts it looks up
`solution-<topic>` by name, then the record's topic skill, then
`solution-<topic>-<plan>`. A skill filed under any other name is invisible to
it, however good the skill is.

Measured on `django__django-13551`: the attempt passed 2 of 2, this pass wrote
a memory holding the correct fix *and* the corner case that had broken the
earlier version — `user.email` is `None` on a model with a custom email field —
and wrote no skill. The store held the answer; the one mechanism that asks for
it saw nothing, and the next run opened at "no skill covers this task".

**A memory is not a substitute.** Memories are recalled through a different
route than the pre-attempt lookup takes, so a solution living only in memory is
one the next run re-derives at full price.

What the solution skill holds, in order of value:

1. **The change that worked**, precisely enough to apply — the file, the
   function, what the line became.
2. **Why that form and not the obvious one.** If an earlier attempt failed
   first, the difference between the two is the most valuable thing on the
   page: *"use `get_email_field_name()` rather than `user.email`, because a
   custom user model has no `email` attribute and the naive form raises
   `TypeError: must be str, not NoneType`"* is worth more than any description
   of the bug.
3. **What the tests checked**, so the next run knows when it is done.

Do not describe the issue. The next run has the issue; what it does not have is
the answer.


### I8 — A partial pass is evidence in both directions

`1 of 2` is not a failure. It is a result that says one part of the change is
CORRECT — the tests were failing before it and pass because of it — and another
part is missing. Only the missing half was ever being recorded.

`attempt-notes.md` and the verdict now name both: `fail_to_pass_passing` and
`fail_to_pass_failing`. Write both down.

* The passing half is **established**. Record it as a finding with the test
  that confirms it, so the next attempt builds on it rather than re-deriving
  it — or worse, rewriting it and regressing a target the run had banked.
* The failing half is the open question, and it is narrower than the original
  issue because part of the issue is now solved.

Measured on `django__django-13551` at 1 of 2: the change had correctly added
the user's email to the token hash and its target test passed. The record kept
only "still failing: test_token_with_different_secret", and the next pass
planned a step for the email handling that already worked.

"The email belongs in the token hash — confirmed by its own target test; what
is still missing is X" is worth more than either half stated alone.


### I9 — Memory is this session; a skill is what survives it

The two stores have different lifetimes, and that — not importance — decides
where something goes.

**Memory holds what is true of THIS run.** The exchange, the attempt log, which
container was used, what this particular agent tried and in what order, the
state a later stage of the same session needs. It is working context. It is
allowed to be long, specific and disposable, because nothing outside this
session will read it.

**A skill holds what is true AFTER this run ends.** The change that worked, the
corner case that broke the obvious version, the method. Anything a future task
on this subject would want, and anything a later run would otherwise pay to
re-derive.

The test is one question: **would a run that never saw this session want it?**

| the exchange, the transcript, the diff of this attempt | memory |
| "this attempt tried X and the tests said Y" | memory |
| the change that made the target tests pass | **skill** |
| why that form beat the obvious one | **skill** |
| a corner case that cost an attempt to find | **skill** |

Getting this backwards is not a filing error, it is a lost result. Measured on
`django__django-13551`: the attempt passed 2 of 2, and the fix — with the
corner case that had broken three earlier runs — was written as a memory. It
was correct, it was well written, and it died with the run, because the
pre-attempt lookup reads skills.

The failure mode is asymmetric. A session fact written as a skill is clutter
that reconciliation can merge away later. A durable finding written as a memory
is gone, and the next run re-derives it at full price.
