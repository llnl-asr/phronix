---
name: branch-dimensionless-function
description: Research on the UnitSystem._collect_factor_and_dimension Function branch (sympy/physics/units/unitsystem.py, lines ~192-196): what minimal fix stops it passing through non-dimensionless-checked arg dimensions, causing the exp()-of-dimensionless-ratio ValueError bug.
subject: branch-dimensionless-function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch dimensionless function |
| `I2` | Instructions | How to solve branch dimensionless function |
| `I3` | Instructions | Fallback approaches for branch dimensionless function |
| `I4` | Instructions | Steps to solve branch dimensionless function |
| `X1` | References | Tried: coerce-dimensionless-in-function-branch |
| `X2` | References | Tried: raise-on-non-dimensionless-function-arg |
| `X3` | References | Tried: simplify-dims-and-fix-multiarg-return-arity |
| `X4` | References | Tried: central-dimension-normalization-helper |
| `X5` | References | Sources consulted for branch dimensionless function |
| `X6` | References | What has been investigated about branch dimensionless function |
| `X7` | References | Where research on this subject stands |

## Instructions

### I1 — How to evaluate a change to branch dimensionless function

Figure of merit: **correct_dimension_detection_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where SI._collect_factor_and_dimension(expr) (a) does not raise ValueError when the true dimension is dimensionless (e.g. exp/sin/cos/log of a dimensionless combination, alone or nested inside Add/Mul/Pow), returning (factor, Dimension(1)) or equivalent recognized-as-dimensionless result, AND (b) still raises ValueError (or returns a non-dimensionless Dimension) when the true dimension is not dimensionless.

Cases differ along: argument_dimensionless, context, expect_error, function_kind.

### I2 — How to solve branch dimensionless function

Try these in order, ONE at a time. Ranked by measured **correct_dimension_detection_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

1. `A14` **coerce-dimensionless-in-function-branch** — worked, see X1.
2. `A15` **raise-on-non-dimensionless-function-arg** — refuted, see X2.

See `research_rank` for the full ranking.

### I3 — Fallback approaches for branch dimensionless function

If the leading approach fails, these were also measured, ranked by the same metric — both already **worked** in a trial, so either is a safe fallback rather than a guess:

**`A3` simplify-dims-and-fix-multiarg-return-arity** — worked, see X3.

**`A4` central-dimension-normalization-helper** — worked, see X4.

### I4 — Steps to solve branch dimensionless function

The steps that solve branch dimensionless function, in order. Run them.

1. `probe_reproduce_dimension_issue(...)` — Reproduce the issue
2. `probe_read_file_region(...)` — Read unitsystem.py Function branch vs Pow branch
3. **Design the fix** (judgement — no tool for this)
   Decide the Function branch should coerce each arg's collected dimension to Dimension(1) when self.get_dimension_system().is_dimensionless(dim) is True, leaving non-dimensionless arg dimensions unchanged, and return a single combined dimension for the whole Function call rather than one dimension per arg.
4. `probe_apply_and_score(...)` — Edit unitsystem.py
5. `probe_find_call_sites(...)` — Verify call-site unpacking arity
6. `probe_run_python_snippet(...)` — Re-run issue reproduction
7. `probe_run_pytest_selection(...)` — Run existing test suite

## Rules

## References

### X1 — Tried: coerce-dimensionless-in-function-branch

In UnitSystem._collect_factor_and_dimension's Function branch (sympy/physics/units/unitsystem.py), coerce each arg's dimension to Dimension(1) when is_dimensionless() is true, mirroring what the Pow branch already does; leave non-dimensionless args untouched.

**Hypothesis**: The Function branch (for exp/log/etc.) never checks is_dimensionless() on its args' dimensions the way the Pow branch does, so a dimensionless-but-not-literal-Dimension(1) argument (e.g. second/(farad*ohm)) is passed through as its raw non-trivial Dimension object; this later fails equality against Dimension(1) in the Add branch, causing the reported ValueError. Coercing dimensionless args to Dimension(1) fixes it.

**Status**: worked. A tuning-stage trial applied this coercion (combined with the arity fix in [[branch-dimensionless-function#X3]]) and confirmed it fixes the exp()-of-dimensionless-ratio bug.

### X2 — Tried: raise-on-non-dimensionless-function-arg

REFUTED candidate: make the Function branch strict — raise ValueError whenever an argument's dimension is not dimensionless, instead of just coercing dimensionless args to Dimension(1) and leaving non-dimensionless args alone.

**Hypothesis**: A stricter Function branch that requires ALL args of a Function to be dimensionless (raising otherwise) would be a cleaner/more correct fix than selectively coercing. Refuted by test_factor_and_dimension in sympy/physics/units/tests/test_quantities.py (~line 353-356): `pH = -log(cH)` where cH has dimension amount_of_substance/volume (NOT dimensionless) is an existing, currently-passing assertion that a strict raise-always fix would break.

**Status**: refuted, do not retry (two independent tune-stage trials both failed against test_factor_and_dimension).

### X3 — Tried: simplify-dims-and-fix-multiarg-return-arity

In sympy/physics/units/unitsystem.py _collect_factor_and_dimension, Function branch (~line 192-196): after computing fds=[(factor,dim) for each arg], replace each arg's dim with Dimension(1) when self.get_dimension_system().is_dimensionless(dim) is True, and return a SINGLE combined dimension (Dimension(1) if all args dimensionless, else the non-dimensionless one) instead of splatting one dimension per arg.

**Hypothesis**: The Function branch has two independent defects: (1) it never coerces a dimensionless-but-not-literally-Dimension(1) arg dimension the way Pow does, causing the exp() ValueError in the issue; (2) it returns an oversized tuple for multi-argument functions, which silently breaks any multi-arg Function whose callers unpack exactly 2 values. A fix must be measured against both: exp(second/(farad*ohm)) and a multi-arg function call.

**Status**: worked. A tuning-stage trial ("coerce dimensionless arg dims + return single 2-tuple dim instead of splatting one dim per arg") applied exactly this combined fix and it worked.

### X4 — Tried: central-dimension-normalization-helper

Instead of patching the Function branch (or Pow branch) individually, add a small helper on UnitSystem (e.g. `self._normalize_dim(dim)`, called at the top of `_collect_factor_and_dimension`) that every branch calls on its computed `arg_dim`/`dim` right after the recursive call returns, collapsing a dimensionless-but-non-trivial Dimension to Dimension(1) in one place.

**Hypothesis**: The real defect is architectural: multiple branches (Pow, Function, Derivative, Add) each need to know whether a sub-dimension is dimensionless, but only Pow currently does the check. If dimension normalization is centralized in one helper called wherever a recursive `_collect_factor_and_dimension` result's dimension is used, future branches (and Derivative/Add today) get the same correctness for free, not just Function.

**Status**: worked. A tune-stage trial confirmed centralizing normalization in a single UnitSystem._normalize_dim helper, called after every recursive _collect_factor_and_dimension call site (Mul, Pow, Add, Derivative, Function, terminal Dimension), fixes the exp()-of-dimensionless-ratio bug without special-casing Function alone.

### X5 — Sources consulted for branch dimensionless function

Root-cause read of sympy/physics/units/unitsystem.py (Function branch ~lines 192-196 vs Pow branch ~167-172); fix applied and verified locally (not committed to source, per aspect instructions).

### X6 — What has been investigated about branch dimensionless function

Ground already covered by research on this subject: the Function branch's missing is_dimensionless coercion (X1), the multi-arg return-arity bug (X3), and the case for centralizing normalization across all branches (X4).

A batch of pylint ignore-paths/_discover_files investigation notes were previously recorded here by mistake — that content belongs to a sibling phronix task on a different repo entirely. It has been moved out; the canonical pylint ignore-paths writeups live at [[pylint-dev-pylint-7080]] and [[pylint-discover-files-ignore-paths]]. Do not re-add pylint/_discover_files content to this skill — this subject is sympy dimension handling only.

### X7 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **correct_dimension_detection_rate** (max, target 1.0).

**Established (worked in a trial)**
- coerce-dimensionless-in-function-branch ([[branch-dimensionless-function#X1]])
- simplify-dims-and-fix-multiarg-return-arity ([[branch-dimensionless-function#X3]])
- central-dimension-normalization-helper ([[branch-dimensionless-function#X4]])

**Refuted**
- raise-on-non-dimensionless-function-arg ([[branch-dimensionless-function#X2]])

**Still open**
- aspect not yet answered: function_branch_fix_shape
- aspect not yet answered: regression_risk_non_dimensionless_function_args
- aspect not yet answered: other_function_like_nodes_affected

**Where the detail is**
- coerce-dimensionless-in-function-branch: Root-cause read of sympy/physics/units/unitsystem.py (Function branch ~lines 192-196 vs Pow branch ~167-172).
- simplify-dims-and-fix-multiarg-return-arity: Direct read of sympy/physics/units/unitsystem.py lines 152-200; the return statement `*(d[1] for d in fds)` was the arity bug.
- central-dimension-normalization-helper: Structural read of sympy/physics/units/unitsystem.py: Pow (167-172), Add (173-184), Derivative (185-191), Function (192-196).

**Caveat**: `research_status`/`research_rank` calls for this topic have previously returned pylint-dev__pylint-7080's approach list instead — a tool-level statefulness bug, not evidence these three are unmeasured. Trust this block's status text over those tools' output for this subject.
