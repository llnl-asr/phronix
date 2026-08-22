---
name: phronix-trial-reconcile
description: What to do after several approaches have been tried against the real tests — merge the winner with whatever the losers did better, or, when none worked, find the assumption all of them shared.
subject: reconciling the results of parallel solution trials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Read the table as evidence about the ranking |
| `I2` | Instructions | Something worked: merge, keeping the winner's spine |
| `I3` | Instructions | Nothing worked: find the shared assumption |
| `I4` | Instructions | Score the result on outcome, cost, and transfer |
| `R1` | Rules | A losing approach is not wrong in every part |
| `R2` | Rules | Do not refine the least-bad candidate |
| `X1` | References | Why all-failed is the more informative case |

## Instructions

### I1 — Read the table as evidence about the ranking

You are given one row per approach: which plan, how far it got on the task's own target tests, whether it solved it.

That table has already tested something research could only estimate. Approaches were ranked before any of them was attempted, against a figure of merit measured on a corpus research built itself. The trials tested that ranking against the real tests, and the table says whether it was right.

Record that. "The metric ranked B first and C solved it" is a finding about the metric, and the next task on this subject inherits it.

### I2 — Several passed: the solution is what they agree on

More than one candidate passing the benchmark's own tests is the best evidence a
research pass can produce — several independent readings of the problem, each
tried against the real target tests, each verified rather than argued.

Write the solution skill out of the ones that **passed**:

- what they have in common is the fix. If two passing candidates both change
  the same function in the same direction, that is the answer, and it is
  confirmed twice.
- where they differ, prefer the smaller change. Both passed, so the extra work
  in the larger one bought nothing measurable.
- record that it was confirmed by more than one candidate. A later task should
  know the difference between "this worked once" and "three readings converged
  on this".

The ones that **failed** become lessons in the same skill, one line each, saying
what was tried and what the tests showed. Be precise about what failed: the
implementation, or the idea. An attempt whose code did not fire tells you about
the code — writing "this approach does not work" retires an idea that was never
tested, and every later task inherits that.

### I2b — Exactly one worked: merge, keeping the winner's spine

`skill_load` the winning approach's skill and the losers'. Write ONE skill for this subject:

- the winner's steps are the spine — they are what produced the fix;
- fold in anything a loser did **better**: a cheaper check, a more direct tool call, a step that generalises where the winner's is specific;
- retire the rest by name, one line each on what the tests showed.

Merging is not concatenation. A merged skill that contains every step of every approach is longer, slower and no more correct than the winner alone.

### I3 — Nothing worked: find the shared assumption

Do not pick the least-bad and refine it. That is the one move that cannot find the problem.

Several independent approaches failing is evidence about the **subject**: they share something false. Work it in this order:

1. Name what every approach took for granted — the file that produces the behaviour, the shape of the fix, what the test is actually asking for. Write it as a claim that could be false.
2. Check that claim with a command whose output settles it. A run, not an argument.
3. Say which of the failures the claim explains. One that explains one failure out of four is probably not it.
4. Then produce candidates against the corrected understanding and record them with `research_add_approach`.

### I4 — Score the result on outcome, cost, and transfer

State all three plainly for whatever you write, in this order:

| | what to say |
| --- | --- |
| outcome | does it produce the fix, on this task's tests |
| cost | roughly how many tokens and how long |
| transfer | how much would still apply to a DIFFERENT task in this subject |

A skill that solves one instance and generalises to none is worth less than a slightly slower one that transfers. The next task inherits the skill, not the instance.

## Rules

### R1 — A losing approach is not wrong in every part

They failed as wholes. A candidate that got two of three target tests passing had most of it right, and discarding it entirely throws that away.

Take the parts that were measured to work. Say which trial each borrowed step came from, so a later correction knows what it is correcting.

### R2 — Do not refine the least-bad candidate

When every approach fails, the tempting move is to take the one that got furthest and adjust it. It feels like progress and is the reason a task can burn every retry without the diagnosis moving.

Furthest is not closest. An approach that passes two tests by coincidence of ordering is not nearer the fix than one that passes none for a comprehensible reason.

## References

### X1 — Why all-failed is the more informative case

One approach failing says that approach was wrong. Four independent approaches failing says something they all believed was wrong — and that is a much stronger, much more useful signal, because it points at the subject rather than at a candidate.

The cost of missing it is high: the shared assumption survives into every later attempt, and the research record grows more detailed and more confident about the wrong area. Learning turns exploration into conviction, and this is the moment to prevent that.
