---
name: phronix_verification
description: The predictor/corrector discipline: every learned or healed thing needs a deterministic check; the five-facet verifier spec (assumptions, inputs, constraints, invariants, outputs); what built-in structural correctors cover; how to read a verdict (fail vs error vs inconclusive). Load before writing a corrector (verify_new) or acting on one that failed, when a check is red on every machine missing a dependency, a spec has no constraints, or a corrector passes because it checks nothing.
---
Cross-references: [[capability_builder]], [[lessons]], [[knowledge]], [[phronix_self_learning]], [[phronix_self_healing]], [[phronix_privacy]]

# Deterministic correctors that prove learned and healed things still hold

Converted from the dftracer-agents skill `phronix-verification` (subject: deterministic correctors that prove learned and healed things still hold). Source description: The predictor/corrector discipline: why every learned or healed thing needs a deterministic check, the five-facet verifier spec (assumptions, inputs, constraints, invariants, outputs), what the built-in structural correctors cover, and how to read a verdict. Load before writing a corrector or acting on one that failed.

Its labels (`I1`, `R1`, `X1`, ...) and `[[phronix-...]]` links are kept as written: a `[[phronix-a-b]]` link is now the capability `phronix_a_b`.

**Overlap with the store's framework capabilities:** capability_builder already enforces the same discipline for capabilities: every capability is a predictor-validator-corrector loop, the validator is separate and deterministic, 'a failed assumption is Verdict.assume: inconclusive, never a failure' (= R3), checks.json run in a sandbox (= I4), capability_verify (= verify_run), and 'never loosen the check to pass' (= R6). R8 (built-in structural correctors) matches capstore.validate_bundle. Strong candidate to merge into capability_builder.

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

### Using the tools (capability)

- Render the procedure with `phronix_verification_plan` (goal + facts), work through the checklist in order, then submit the record (fields: `claim`, `assumptions`, `inputs`, `constraints`, `invariants`, `outputs`, `deterministic`, `ran`, `verdict`, `diagnosis`) to `phronix_verification_check`; a step is done only when the check passes.

## References

### X1 — What triggers a corrector run

After recording anything: [[phronix-self-learning#I6]]. After any repair:
[[phronix-self-healing#R4]].

### X2 — Promotion is gated on correctors passing

`phronix contribute` refuses to ship an artifact whose corrector fails or is
broken. See [[phronix-privacy#R5]] for the parallel privacy gate.

## Constraints

- Correctors are deterministic (R2).
- Never remove what a check checked to make it pass (R6).
- Do not author correctors for what the structural correctors already cover (R8).
- Promotion (phronix contribute) is refused while a corrector fails or is broken (X2; parallel privacy gate [[phronix-privacy#R5]]).

## Corner cases

- An assumption miscategorised as a constraint is the most common authoring error (I5 case 4).
- A rotted claim keeps the old statement as a dated note so someone on an older version still finds their answer (I5 case 2).
- A verifier that mutates what it verifies invalidates its own result (R4).
- orphaned_verifiers, broken_verifiers and never_run are coverage that is not really there (I1).
- P1 (source pitfall) — Environment preconditions written as constraints: The most common authoring error. A dependency check under `constraints` turns every machine without that dependency red. Move it to `assumptions`, where a failure correctly reads as "could not run here".
- P2 (source pitfall) — A scaffolded corrector left unfinished: `verify_new` without a `source` produces a spec with no constraints. It is reported as a malformed spec rather than passing — but until you notice, the subject looks covered in `verify_coverage()`. Finish it in the same session.
- P3 (source pitfall) — Correctors that pass because they check nothing: A constraint like `lambda ctx: True`, or one asserting something the code cannot help but satisfy, produces permanent green. Ask of every constraint: what change to the world would turn this red? If the answer is "none", delete it.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector

- Predictor `phronix_verification_plan`, validator `phronix_verification_check`. A failed verdict comes here: repair the record (or the step that produced it), then plan and validate again. The same failure twice stops the loop: change approach, or ask the user.
- `claim_falsifiable` failed: write the claim so it could be wrong (I2)
- `claim_present` failed: state the claim the corrector checks (I2)
- `has_constraint_or_output` failed: a spec with no constraints and no outputs cannot fail; state at least one (R5)
- `env_in_assumptions` failed: an environment precondition is an assumption, not a constraint: move it (I5 case 4, R3)
- `no_trivial_constraint` failed: a constraint nothing can turn red checks nothing: delete or replace it (R6, P3)
- `deterministic` failed: remove model calls, clock branching, randomness and unneeded network from the check (R2)
- `ran` failed: verify_run(name=...): a corrector that never executed is not evidence (I4, R1)
- `verdict_known` failed: verdict is pass, fail, error (broken corrector) or inconclusive (assumption failed) (R3, R7)
- `red_diagnosed` failed: diagnose a red result into one of the four causes before changing anything (I5)
- `goal is required` from the planner: restate the concrete target (the task, file, run or stage) and plan again.
- A check that is wrong about a correct record: reproduce it with a new entry in checks.json and `capability_update` this capability; never loosen the record to pass.

## Self-heal

- A broken corrector (error) is worse than a missing one: fix or remove it in the same session (R7, P2).
- A tool here failed or ruled wrongly: follow `capability_builder`'s Self-heal (reproduce with a check, `capability_update`, user approval) rather than working around it.

## Self-learn

- What is explored while applying this procedure (a new workload, software, tool, system or way of doing it) becomes a capability: see capability_builder (Rules).
- Run the corrector after recording anything ([[phronix-self-learning#I6]]) and after any repair ([[phronix-self-healing#R4]]) (X1).
- A new pitfall of this procedure: `lesson_add` it to this capability with its evidence (a run, a log line, the user's words).

## What works

- verify_coverage -> falsifiable claim -> five facets -> verify_new + verify_run; in the capability store the same loop is predictor -> validator -> Corrector with checks.json (2026-09-15).
- `phronix_verification_plan` -> follow the checklist -> `phronix_verification_check` pass is the verified loop for this procedure (checks.json, conversion 2026-11-13).
