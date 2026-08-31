---
name: phronix-task-research
description: Turn one task's open failure into a fix — read the tracker record, diagnose the specific error, and write the fix into the task's solution skill for the next attempt to execute.
subject: fixing the specific failure a task is stuck on
type: skill
---


# Researching one failure

An attempt ran and did not fully succeed. You are given the task's `tracker.md`
— what is established, what is still open, what has been ruled out — and the
execution summary of the attempt that just failed.

Your job is narrow and it is not "investigate the task". It is: **take the
specific error that is open, work out the fix, and write that fix into the
task's solution skill** so the next attempt executes it rather than rediscovering
it.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Start from the open failure, not from the issue |
| `I2` | Instructions | Keep what is established — a fix that regresses it is not a fix |
| `I3` | Instructions | Do not re-try what is ruled out |
| `I4` | Instructions | Write the fix into the solution skill, executably |
| `I5` | Instructions | You are on a clock; an unfinished diagnosis is still worth writing |
| `I6` | Instructions | Say the problem, the approach and the answer, as you go |
| `I7` | Instructions | Read the lessons first, and write one back |
| `I8` | Instructions | Retrieve the conversation a turn at a time; never read it whole |
| `R1` | Rules | Diagnose the error, do not improve the area |


## Instructions

### I1 — Start from the open failure, not from the issue

The issue describes the original bug. The tracker's `Open` section describes
what is *still wrong after the last attempt*, and those are different questions
by the second attempt.

Read `Open` first. It names a test and the assertion or error behind it. That
error is your subject. Everything else in the record is context for it.

If `Open` names an error with a file and a line, go there first. A traceback is
a diagnosis someone already did for you.

### I2 — Keep what is established — a fix that regresses it is not a fix

The `Established` section lists target tests that now pass and facts the tests
confirmed. Those are banked.

A proposed fix that would break one of them is not progress, however well it
addresses the open failure. Say so explicitly in the solution skill: what must
keep working, and which part of the existing change produces it.

The common shape of this mistake is rewriting the whole of a partly-correct
change because part of it is wrong. Change the part that is wrong.

### I3 — Do not re-try what is ruled out

`Ruled out` exists so the loop does not repeat itself. Each entry says what was
tried and why it is not the answer.

If your diagnosis lands on something already there, that is a signal you have
the wrong diagnosis — not permission to try it again because this time it will
be done properly. Say what is different, or find another cause.

### I4 — Write the fix into the solution skill, executably

The output is not a report. It is an update to the task's solution skill that
the next attempt loads and follows.

What that means concretely:

* **The change**, precisely enough to apply — the file, the function, and what
  the line becomes. Not "handle the None case" but the expression.
* **Why this form**, when an obvious alternative exists and fails. This is the
  most valuable line you can write, because it is what stops the next attempt
  taking the obvious route: *"use `get_email_field_name()` rather than
  `user.email`, because a custom user model has no `email` attribute and the
  naive form raises `TypeError: must be str, not NoneType`"*.
* **What must keep passing**, from `Established`.

Update the existing solution skill rather than founding a second one. Two skills
for one task split every later retrieval.

### I7 — Read the lessons first, and write one back

The skill you are updating has a `LESSONS.md` beside it, attached with it. That
file is what earlier attempts on this task already tried and how each one
failed. Read it before you diagnose: a revision that proposes something already
recorded there spends a whole try learning what was on file before you started.

They are separate files on purpose — "how do I do this" and "what went wrong
last time" are different questions — and `skill_load` returns the instructions
unless you ask for the lessons by name. The skill's `## References` names the
call.

So write BOTH halves:

* `skill_write` — the corrected fix, as `I4` describes it.
* `skill_write_lesson` — what the attempt you are diagnosing tried, and how it
  failed, naming the tests it broke. A patch that fixes nothing and regresses
  seven tests is a lesson; without it the try after this one repeats it.

Measured on a task where this was missing: the skill's instructions were empty
and the only thing the task had learned sat unread in `LESSONS.md`, so tries 2
and 3 both loaded the skill and got nothing.

### I5 — You are on a clock; an unfinished diagnosis is still worth writing

You have a bounded budget, and it is deliberately short — a diagnosis that needs
an hour is usually a diagnosis that has lost its subject.

If the budget runs out before you are certain, write what you have: the
narrowest statement of the cause you can support, and what you would check next.
That is worth more than nothing, and the next pass is given more time precisely
because this one reported where it got to.

Do not pad an uncertain diagnosis into a confident one to fill the space. A
wrong fix written confidently costs the next attempt entirely; an honest "the
cause is in X, I could not confirm which of two forms" costs it a few minutes.

### I6 — Say the problem, the approach and the answer, as you go

Three lines, in this form, so a pass can be audited from its trace without
anyone reading a transcript:

```
PROBLEM:  <the one failure you are solving, in a line>
APPROACH: <what you are about to check, and why that would settle it>
ANSWER:   <the fix, or the narrowest statement of the cause you can support>
```

`PROBLEM` comes first, before you look at anything — writing it is how you find
out whether you have one subject or three. `APPROACH` comes before each thing
you try, and again when you change direction. `ANSWER` comes last, once.

Write the same three into the report file you are given, so they outlive the
trace.

**A pass that reports only `ANSWER` cannot be audited.** The value of `APPROACH`
is that a wrong answer can be traced to the step that produced it, and a right
one can be trusted for a reason rather than because it happened to pass. A run
of these lines across several attempts is also the fastest way to see the loop
going in circles: the same `APPROACH` twice, with different words.

If you finish without an `ANSWER`, say so in one — "ANSWER: could not confirm
whether X or Y; next check is Z" is a result. Silence is not.

### I8 — Retrieve the conversation a turn at a time; never read it whole

The task record and the summary are attached. The FULL conversation is not, and must not be read whole: it is every turn appended and never rewritten, so it grows with the task and is largest exactly when the context is tightest. Reading it whole is what runs the window out — measured on pytest-5495, an attempt forty steps in added one 2000-line file and the request came back `400 ContextWindowExceededError`, killing the try with no patch.

Use the tools instead, in this order:

1. `conversation_outline()` — turn numbers, titles and sizes. Cheap; start here.
2. `conversation_search("<symbol, file or approach>")` — answers the question a revision pass actually has: has this been tried already?
3. `conversation_turn(-1)` — the most recent turn, which says what just failed. Negative numbers count from the end.

Ask for a turn when the summary leaves you guessing. Do not ask for all of them: the point is that only the turn you need enters the context.

## Rules

### R1 — Diagnose the error, do not improve the area

The open failure is one specific error. Fix that.

An attempt that arrives with a redesign of the surrounding code has changed the
subject: the tests are not asking for a better module, they are asking for one
assertion to pass. A larger change is also a larger surface for regressing what
is already established.

If the correct fix genuinely requires restructuring, say so and say why the
narrow fix cannot work — that claim is checkable, and "it would be cleaner" is
not a reason the tests can read.
