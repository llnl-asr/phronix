---
name: phronix-explore-idea
description: How to explore one idea from the plan — try it against the failing case, measure what actually changes, and record the finding so the solution can be built from it.
subject: explore one idea from the plan
type: skill
---


# Exploring one idea

You have one idea from the plan and two minutes. Two other agents are exploring
the other two right now; none of you can see the others' work, and the solution
is built from all three findings together.

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I0` | Instructions | You are exploring ONE STEP, not the whole fix |
| `I1` | Instructions | Try it, do not describe it |
| `I2` | Instructions | Reach for a tool before deriving by hand |
| `I3` | Instructions | Record what happened, including that it failed |
| `I4` | Instructions | What the finding has to contain |
| `X1` | References | Do not build the solution here |
| `R1` | Rules | Why the ideas are explored in parallel and not in order |

## Instructions

### I0 — You are exploring ONE STEP, not the whole fix

The plan decomposes the problem into an ordered method and hands you one step of
it — see [[phronix-research-plan]] `I5b`. Your job is to find how THIS step is
done, concretely enough that someone could carry it out: the file, the function,
the change.

Record each way you find with `research_add_approach(..., aspect="<this step>")`,
so it is attached to the step it belongs to rather than floating free.

**Find SEVERAL ways to do this step, and make them genuinely different.**

Two ways of doing one step become two complete solutions that differ in exactly
one place — a real alternative. Two ways that touch the same line are one way
described twice, and the pipeline will race them as if they were two.

The same independence rule that governs the steps governs the ways within a step
(see [[phronix-research-plan]] `I6`): if two ways would be carried out in the
same place, they are the same way. Move along an axis instead — do it earlier or
later in the flow, do it in the caller rather than the callee, change the input
rather than the handling of it, configure it rather than code it.

```
ONE WAY, DESCRIBED TWICE
  - "return the parent when __init__.py is absent"
  - "walk up while __init__.py exists, then return"     same line, inverted

GENUINELY DIFFERENT WAYS for "choose the sys.path root"
  - compute it from the file's own package chain        expand_modules.py
  - ask astroid for the modpath and derive the root     modutils
  - let the caller pass the root it already knows       pylinter.py
```

Record each with `research_add_approach(..., aspect="<this step>")` and a
hypothesis that says what would show it wrong. They are explored and raced in
parallel, so a way that costs nothing to add still costs a container to try —
which is worth it for a real alternative and wasted on a rename.

That distinction is what this pipeline got wrong before it worked in steps: on
`pylint-dev__pylint-7114`, four differently-named ideas all changed
`get_python_path`, and the candidate built from them rewrote the same loop.
Three tries, five containers each, every candidate scoring zero.

**Finding that the step needs NOTHING is also a result.** Say so. A method that
carries a step which turns out to be unnecessary wastes every attempt that
implements it, and the next session re-derives the same emptiness.


### I1 — Try it, do not describe it

The point of the phase is evidence, and the only way to get evidence is to make
the change and run something. An idea that was reasoned about and never
attempted contributes an opinion, and the build stage cannot tell an opinion
from a result.

You have a worktree of your own. Edit it, run the failing case, run the tests
around it, and see what happens. Nothing you do here reaches the patch — the
worktree is thrown away — so the cost of trying is only the trying.

### I2 — Reach for a tool before deriving by hand

Call `capability_list` first. A `probe_` tool that reproduces this failure or
runs this check returns in one call what costs five by hand, and under a
two-minute budget those five are most of your time. See
`phronix-research-as-tools`.

If you do something twice, build it with `capability_new` instead of doing it a
second time.

### I3 — Record what happened, including that it failed

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)`
as you go, and the finding for the idea before you finish.

**An idea that did not work is a result, not a wasted stage.** It is often the
most valuable of the three: it removes a whole direction the build stage would
otherwise have to consider, and it stops the next task on this repository
spending its own two minutes rediscovering the same dead end.

Say precisely what failed. "Did not work" tells the build stage nothing; "the
change makes the reported case pass and breaks four other tests, all of which
assert the relative form" tells it exactly where the real answer lies.

### I4 — What the finding has to contain

* What was tried, concretely enough to redo — the file, the function, the change
* What happened when it ran, in numbers where there are numbers
* What that rules in and what it rules out
* What is still unknown, if the two minutes ran out mid-way

Partial is fine and must be marked partial. A measurement over two cases is a
measurement over two cases, and the build stage can weigh it correctly only if
it knows how thin it is.

## Rules

### R1 — Why the ideas are explored in parallel and not in order

Ideas are independent by construction: the plan is asked for angles that can
each be answered without waiting on the others. Run in sequence they would cost
six minutes and the third would be shaped by the first two, which sounds like an
advantage and is not — it produces three variations of one reading of the
problem instead of three readings.

## References

### X1 — Do not build the solution here

You are exploring one idea, not deciding the answer. The build stage sees all
three findings and yours alone cannot tell which is best — an explorer who
writes the final solution is deciding from one third of the evidence.
