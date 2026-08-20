---
name: phronix-verification
description: The predictor/corrector discipline: why every learned or healed thing needs a deterministic check, the five-facet verifier spec (assumptions, inputs, constraints, invariants, outputs), what the built-in structural correctors cover, and how to read a verdict. Load before writing a corrector or acting on one that failed.
subject: deterministic correctors that prove learned and healed things still hold
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Run what already exists, first |
| `I2` | Instructions | Decide what the claim actually is |
| `I3` | Instructions | Fill the five facets in order |
| `I4` | Instructions | Write it and run it |
| `I5` | Instructions | Diagnose a red result before changing anything |
| `R1` | Rules | Nothing is learned or healed until its corrector runs |
| `R2` | Rules | Every check must be deterministic |
| `R3` | Rules | A failed assumption is inconclusive, never a failure |
| `R4` | Rules | An invariant violation invalidates the whole run |
| `R5` | Rules | A spec with no constraints and no outputs is rejected |
| `R6` | Rules | Never make a check pass by removing what it checked |
| `R7` | Rules | `error` is not `fail` |
| `R8` | Rules | Do not duplicate the built-in structural correctors |
| `X1` | References | What triggers a corrector run |
| `X2` | References | Promotion is gated on correctors passing |

## Instructions

### I1 — Run what already exists, first

```
verify_coverage()   # which subjects have a corrector, which do not
verify_run()        # everything: built-in structural + authored spec
```

`verify_coverage()` also reports `orphaned_verifiers` (target gone),
`broken_verifiers` and `never_run`. All three are coverage that is not really
there, and all three need fixing.

### I2 — Decide what the claim actually is

Write it so it **could be wrong**. "The flag is spelled `--jobs`" is falsifiable.
"The service works" is not, so a corrector for it proves nothing while looking
like coverage.

### I3 — Fill the five facets in order

1. **assumptions** — what must already be true for this check to mean anything?
   Dependency installed, service reachable, file present.
2. **inputs** — what does the check read? Declare each with a `resolve` callable
   so a missing one is named rather than surfacing as an exception later.
3. **constraints** — the claim itself.
4. **invariants** — what must the check not disturb? Sampled before and after.
5. **outputs** — what must exist afterwards, and in what shape.

### I4 — Write it and run it

`verify_new(kind=..., target=..., claim=..., source=...)`, then
`verify_run(name=...)`. A corrector that has never executed is not evidence; it is
an untested claim about an untested claim.

### I5 — Diagnose a red result before changing anything

Four possibilities, with different responses:

1. **The claim was always wrong** — fix the entry, and record what made the wrong
   diagnosis plausible.
2. **The claim has rotted** — true once, the world moved. Update it and keep the
   old statement as a dated note so someone on an older version still finds their
   answer.
3. **The corrector is wrong** — it tests something the claim never said. Fix the
   corrector.
4. **An assumption was miscategorised as a constraint** — move it. This is the
   most common authoring error.

## Rules

### R1 — Nothing is learned or healed until its corrector runs

Learning and healing are *predictions*. A model that is right most of the time
still writes a confidently wrong entry often enough to poison a shared store — and
the poison is silent, because a wrong entry reads exactly like a right one. Run
`verify_run(target=...)` after every write and every fix.

### R2 — Every check must be deterministic

No model calls, no wall-clock or calendar branching, no randomness, no network
unless the claim is about the network. If two people run the corrector on the same
artifact and get different verdicts, it is not an anchor. A corrector that asks a
model whether the claim looks right is just another predictor wearing a
corrector's name.

### R3 — A failed assumption is inconclusive, never a failure

`assumptions` and `inputs` gate the run: if a precondition does not hold, the
check could not run *here*, which is not evidence the claim is wrong. Collapse
this distinction and every machine missing a dependency reports red, everyone
learns to ignore the red, and the genuine failures go with it.

### R4 — An invariant violation invalidates the whole run

Invariants are sampled before AND after and compared. A verifier that mutates what
it verifies invalidates its own result, whatever the constraints said.

### R5 — A spec with no constraints and no outputs is rejected

It cannot fail, so it proves nothing — while occupying a slot that looks like
coverage. State at least one condition the claim asserts.

### R6 — Never make a check pass by removing what it checked

A green corrector that verifies nothing is strictly worse than no corrector: it
converts an open question into a false answer.

### R7 — `error` is not `fail`

`error` means the corrector itself raised or its spec is malformed — a broken
check, which is worse than a missing one because it still looks like coverage.
`fail` means the check ran and the claim did not hold. They are reported and
aggregated separately.

### R8 — Do not duplicate the built-in structural correctors

Every skill, capability and agent already gets one automatically: frontmatter and
schema, label uniqueness, index/content agreement, reference resolution, module
compilation, tool docstrings, renderability, privacy. Authored correctors are for
what structure cannot settle — whether the claim about the world is true.

## References

### X1 — What triggers a corrector run

After recording anything: [[phronix-self-learning#I6]]. After any repair:
[[phronix-self-healing#R4]].

### X2 — Promotion is gated on correctors passing

`phronix contribute` refuses to ship an artifact whose corrector fails or is
broken. See [[phronix-privacy#R5]] for the parallel privacy gate.
