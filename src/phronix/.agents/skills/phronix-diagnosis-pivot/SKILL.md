---
name: phronix-diagnosis-pivot
description: What to do when two attempts have failed in exactly the same way — stop refining the change, name what both attempts assumed, and take a genuinely different path.
subject: diagnosing a failure that has stopped moving
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Name the assumption, as a claim that can be false |
| `I2` | Instructions | Check whether your edits even run |
| `I3` | Instructions | Read what the test asks for, literally |
| `I4` | Instructions | Take a different path, and say why it differs |
| `R1` | Rules | An identical failure is evidence, not noise |
| `R2` | Rules | The same edit with better values is not a new approach |
| `X1` | References | What this looks like when it goes wrong |

## Instructions

### I1 — Name the assumption, as a claim that could be false

Ordinary diagnosis asks what was missing, which assumes the last attempt was close. Two identical failures are exactly the evidence against that assumption, so start somewhere else.

Write down what both attempts took for granted, as a claim someone could disprove:

- "the header text is right and only the layout is wrong"
- "this function is the one that produces the output"
- "the test fails because the value is wrong, not because it is absent"

You cannot pivot away from an assumption you have not stated.

### I2 — Check whether your edits even run

Before anything else, confirm the code you changed is executed on this path. A print, a breakpoint, a deliberate exception — something that cannot be true unless your edit runs.

An identical failure across two different patches is the signature of edits that never took effect: a different module shadowing the one you edited, an installed copy rather than the checkout, a branch that is never reached.

### I3 — Read what the test asks for, literally

Take the assertion apart word by word. A containment assertion wants an exact string; a comparison wants an exact value; an exception test wants that exception type and not a subclass.

The failure output usually says both halves — what was wanted and what was produced. Where they differ by a word, the word is the bug. Two capable models have independently written a column named `Domain` while the test asked for `Subdomain`, each refining the logic three times without reconsidering the string.

### I4 — Take a different path, and say why it differs

A different file, a different mechanism, or a different reading of what the test wants. Then state, in one line, what makes it different from what already failed twice.

If you cannot say that, you have not pivoted. `research_ruled_out` lists what has been tried; none of it is worth repeating unchanged.

## Rules

### R1 — An identical failure is evidence, not noise

Same tests, same reason, same text missing. That is a measurement, and it says the idea is wrong rather than the execution.

Treating it as bad luck — retrying, adjusting values, tidying the change — spends the remaining attempts on a question that has already been answered.

### R2 — The same edit with better values is not a new approach

Re-indenting it, moving it, renaming a variable, changing a constant: all the same approach. The check is whether the change would still fail for the reason the last one did.

If your new plan leads back to an edit that has already failed, the diagnosis is what is wrong. Go back to `I1`.

## References

### X1 — What this looks like when it goes wrong

Measured on one task: three attempts added a CLI column, each improving the logic — unconditional, then conditional, then handling host-versus-subdomain correctly — and every one named the column `Domain` while the tests asserted `Subdomain` and `Host`. The mechanism got better each time and the outcome never changed.

Measured on another: every block the learner wrote was about the wrong file entirely, and each attempt saw only that its own patch failed, never that three patches in the same function had failed. The knowledge base grew more detailed and more confident about the wrong area.

Both are the same failure: refinement continuing past the point where the evidence stopped supporting the approach.
