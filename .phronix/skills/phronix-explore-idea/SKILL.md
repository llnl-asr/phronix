---
name: phronix-explore-idea
description: How to explore one idea from the plan — try it against the failing case, measure what actually changes, and record the finding so the solution can be built from it.
---

# Exploring one idea

You have one idea from the plan and two minutes. Two other agents are exploring
the other two right now; none of you can see the others' work, and the solution
is built from all three findings together.

## I1. Try it, do not describe it

The point of the phase is evidence, and the only way to get evidence is to make
the change and run something. An idea that was reasoned about and never
attempted contributes an opinion, and the build stage cannot tell an opinion
from a result.

You have a worktree of your own. Edit it, run the failing case, run the tests
around it, and see what happens. Nothing you do here reaches the patch — the
worktree is thrown away — so the cost of trying is only the trying.

## I2. Reach for a tool before deriving by hand

Call `capability_list` first. A `probe_` tool that reproduces this failure or
runs this check returns in one call what costs five by hand, and under a
two-minute budget those five are most of your time. See
`phronix-research-as-tools`.

If you do something twice, build it with `capability_new` instead of doing it a
second time.

## I3. Record what happened, including that it failed

`research_observe(what=..., worked=true/false, detail=..., stage=..., kind=...)`
as you go, and the finding for the idea before you finish.

**An idea that did not work is a result, not a wasted stage.** It is often the
most valuable of the three: it removes a whole direction the build stage would
otherwise have to consider, and it stops the next task on this repository
spending its own two minutes rediscovering the same dead end.

Say precisely what failed. "Did not work" tells the build stage nothing; "the
change makes the reported case pass and breaks four other tests, all of which
assert the relative form" tells it exactly where the real answer lies.

## I4. What the finding has to contain

* What was tried, concretely enough to redo — the file, the function, the change
* What happened when it ran, in numbers where there are numbers
* What that rules in and what it rules out
* What is still unknown, if the two minutes ran out mid-way

Partial is fine and must be marked partial. A measurement over two cases is a
measurement over two cases, and the build stage can weigh it correctly only if
it knows how thin it is.

## X1. Do not build the solution here

You are exploring one idea, not deciding the answer. The build stage sees all
three findings and yours alone cannot tell which is best — an explorer who
writes the final solution is deciding from one third of the evidence.

## R1. Why the ideas are explored in parallel and not in order

Ideas are independent by construction: the plan is asked for angles that can
each be answered without waiting on the others. Run in sequence they would cost
six minutes and the third would be shaped by the first two, which sounds like an
advantage and is not — it produces three variations of one reading of the
problem instead of three readings.
