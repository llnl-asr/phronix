---
name: phronix-research-as-tools
description: Prefer calling an existing probe tool over re-deriving a fact by hand, and turn any procedure you repeat into a tool the next stage can call in one step.
---

# Research is a tool-building exercise

Every stage of research is under a hard budget, and a stage spends that budget
in two very different ways: *thinking*, which is what the budget is for, and
*re-establishing something already known*, which is what this skill exists to
eliminate.

## I1. Look for the tool before doing the work by hand

Before reproducing a failure, running a check, or extracting a fact from the
tree, call `capability_list` and see whether a `probe_` tool already does it.

A probe returns in one call what a hand-derivation costs five: open the file,
find the region, write a snippet, run it, read the output. Under a budget of
a hundred-odd seconds those five calls are most of the stage.

The store persists across tasks in the same repository, so the tool you want
was very likely built by an earlier task on this same subject.

## I2. Build the tool the second time, not the fifth

The moment you find yourself about to do something you have already done in
this pass — or that the transcript shows another aspect doing — stop and call
`capability_new` instead.

Two things qualify, and nothing else does:

* **A deterministic procedure.** Same inputs, same answer, no judgement. A
  reproduction, a measurement, a check that a condition holds.
* **Something that will be asked again.** By the next aspect, the tune stage,
  a retry, or another task on this repository.

Judgement calls do not become tools. A tool that decides *whether an approach
is right* encodes one opinion as if it were arithmetic; a tool that *measures
what an approach does* is a fact, and the deciding stays where it belongs.

## I3. Name it for the question, not the mechanism

`probe_ignore_paths_applied_recursively` says what it answers.
`probe_run_pylint` says what it runs, and the next stage cannot tell whether it
answers the question at hand without reading its source.

## R1. Why this is where the budget goes furthest

Tuning measures each approach against every instance of the corpus. That is the
same procedure run tens of times, and it is the single largest consumer of the
pass. Built as a tool it becomes tens of fast calls; done by hand it becomes
tens of multi-step derivations, and the stage is stopped by its budget
somewhere in the middle with most approaches unmeasured.

The pass that builds tools early is not slower for having done so. It is the
only version that finishes.

## R2. The tool outlives the task

A probe is the most durable thing research produces. A skill records what was
believed and must be re-read and re-judged; a probe *runs*, and a later task
gets its answer without spending a stage on it.

This is why a tool built on the last try of a failing task is still worth
building. The task may be lost; the next one on that repository starts ahead.

## X1. Do not tool a one-off

A procedure used once, in one task, that nothing will ask again is not a tool —
it is a shell command with ceremony around it. Every tool is listed to every
future agent, and a store full of single-use probes costs every later task the
time to read past them.
