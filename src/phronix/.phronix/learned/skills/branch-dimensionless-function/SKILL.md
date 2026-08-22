---
name: branch-dimensionless-function
description: Research on branch dimensionless function. Covers in sympy/physics/units/unitsystem.py's _collect_factor_and_dimension, the Function branch (around line 192-196) returns the raw dimension of each argument unchanged instead of checking is_dimensionless — should the fix collapse each arg's dimension to Dimension(1) when SI.get_dimension_system().is_dimensionless(arg_dim) is true, mirroring the Pow branch's existing exp_dim collapse pattern at line 170-171; what should happen for functions like exp/log/sin whose argument is NOT dimensionless (e.g. exp(second))? Does current behaviour raise anywhe
subject: branch-dimensionless-function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch dimensionless function |
| `I2` | Instructions | How to solve branch dimensionless function |
| `I4` | Instructions | Steps to solve branch dimensionless function |
| `X3` | References | Tried: fix-add-branch-comparison-logic |
| `X4` | References | Tried: fix-dimension-or-dimensionsystem-class |
| `X5` | References | Tried: function-branch-dimensionless-check |
| `X6` | References | Tried: add-branch-dimensionless-aware-comparison |
| `X7` | References | Tried: function-branch-collapse-dimensionless-arg |
| `X8` | References | Tried: add-branch-dimensionless-tolerant-compare |
| `X9` | References | Sources consulted for branch dimensionless function |
| `X10` | References | What has been investigated about branch dimensionless function |
| `X11` | References | Tried: fix-function-branch-collapse-dimensionless |
| `X12` | References | Tried: collapse-dimensionless-function-and-pow-base |
| `X13` | References | Where research on this subject stands |
















































## Instructions

### I1 — How to evaluate a change to branch dimensionless function

Figure of merit: **correct_dimension_check_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where calling SI._collect_factor_and_dimension(expr) produces the expected outcome: for positive cases (transcendental/generic Function applied to an argument whose Dimension reduces to dimensionless per SI.get_dimension_system().is_dimensionless, e.g. exp(second/(farad*ohm))) it must return Dimension(1) as the second tuple element without raising; for negative cases (

Cases differ along: arg_dimensionless_form, construct, function_arity, function_kind.

### I2 — How to solve branch dimensionless function

Try these in order, ONE at a time. Ranked by measured **correct_dimension_check_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A9` **collapse-dimensionless-function-and-pow-base** — correct_dimension_check_rate 1.000, potential — Extends collapse-dimensionless-in-function-branch: in sympy/physics/units/unitsystem.py's 
2. `A2` **fix-function-branch-collapse-dimensionless** — correct_dimension_check_rate unmeasured, potential — Fix in UnitSystem._collect_factor_and_dimension's `elif isinstance(expr, Function):` branc

...and 10 lower-ranked approach(es); see `research_rank`.### X2 — Tried: collapse-dimensionless-in-function-branch

In UnitSystem._collect_factor_and_dimension's Function branch (sympy/physics/units/unitsystem.py ~line 192-196), collapse each arg's dimension to Dimension(1) when self.get_dimension_system().is_dimensionless(d[1]) is true, mirroring the logic already present in the Pow branch just above it.

**Hypothesis**: The bug is that the Function branch forwards the argument's raw Dimension object (e.g. Dimension(time/(capacitance*impedance))) instead of recognizing it is dimensionally equivalent to 1, so a later Add comparison (dim != addend_dim, structural not dimensional-system-aware) fails. If true, adding the same is_dimensionless collapse used in the Pow branch to the Function branch should fix it without

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: fix-add-branch-comparison-logic

Considered: modify the Add branch (lines 173-184) where the ValueError is actually raised, to treat dimensionless dims as equal. REFUTED — the Add branch's comparison logic is correct; it's correctly detecting a real structural mismatch. The bug is upstream: the Function branch supplies a non-normal

**Hypothesis**: N/A (ruled out) — the exception site is not the root cause site.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: fix-dimension-or-dimensionsystem-class

Considered: fix in Dimension class or DimensionSystem.is_dimensionless itself. REFUTED — both already work correctly; confirmed via the assert in the issue's own reproduction script (`assert SI.get_dimension_system().is_dimensionless(dim)`), which passes even in the buggy pre-fix state. The defect i

**Hypothesis**: N/A (ruled out) — is_dimensionless already returns the correct answer; nothing to fix there.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: function-branch-dimensionless-check

Fix `_collect_factor_and_dimension`'s `Function` branch in sympy/physics/units/unitsystem.py to normalize each arg's dimension to Dimension(1) when is_dimensionless(d[1]) is true, mirroring the existing get_dimensional_expr pattern. 2-line diff. Verified: repro from issue no longer raises ValueError

**Hypothesis**: The root cause is that the Function branch returns the raw (non-normalized) dimension of each arg instead of checking is_dimensionless, so exp(dimensionless-but-not-literally-1 expr) gets mistagged with a non-Dimension(1) dimension; this later fails a plain `!=` comparison in the Add branch. Normalizing in the Function branch (as get_dimensional_expr already does) should fix it without touching Ad

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: add-branch-dimensionless-aware-comparison

Alternative fix considered: instead of fixing the Function branch, patch the Add branch's `dim != addend_dim` check to use is_dimensionless-aware comparison. REJECTED/refuted as not minimal: it would fix the reported symptom (the Add case) but leave _collect_factor_and_dimension's Function branch st

**Hypothesis**: If the defect were in the Add branch's equality semantics rather than upstream in Function's dimension propagation, patching the comparison there would suffice. Refuted by root-cause tracing: the Add branch's check is legitimate/necessary; the actual defect is that Function produces a wrong un-normalized dimension in the first place, so patching Add only would leave other Function-branch callers b

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: function-branch-collapse-dimensionless-arg

In sympy/physics/units/unitsystem.py, UnitSystem._collect_factor_and_dimension, the `elif isinstance(expr, Function):` branch (around line 192-196) currently returns each arg's raw dimension unchanged. Change it to check each arg's dimension with self.get_dimension_system().is_dimensionless(d[1]) an

**Hypothesis**: The Function branch is the only place transcendental functions like exp/log/sin get their dimension computed, and it forwards the raw (non-normalized) argument dimension instead of collapsing it to Dimension(1) when the argument is dimensionally equivalent to 1 (e.g. second/(farad*ohm)). This is why the later Add branch's `dim != addend_dim` check compares Dimension(1) (from "100") against the un-

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: add-branch-dimensionless-tolerant-compare

Instead of touching the Function branch, change the Add branch (unitsystem.py ~173-184) so `if dim != addend_dim:` first checks whether both dims are dimensionless via is_dimensionless before raising, treating any two dimensionless dims as compatible.

**Hypothesis**: If the real defect is that Add-comparison treats two different-but-both-dimensionless Dimension objects as unequal, patching the comparison there (rather than normalizing upstream in Function) would fix the reported case without touching Function's generic behavior. Falsified if downstream code still needs the exp() call itself to carry a normalized Dimension(1) (e.g. if the returned expression's 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Sources consulted for branch dimensionless function

- Investigation of sympy/physics/units/unitsystem.py at base commit 514579c655bf; reproduced via sympy.physics.units + exp() expression from the issue
- Reproduction script assertion checked against base commit 514579c655bf
- Root-caused via manual tracing of Add.args and _collect_factor_and_dimension in sympy/physics/units/unitsystem.py (~line 152-200, base commit 514579c655bf); pattern copied from sibling method get_dime
- issue.md reproduction; sympy/physics/units/unitsystem.py:152-200 (base commit 514579c655bf)
- tmp/research/aspect-reproduce.md — manual repro with `SI._collect_factor_and_dimension(100 + exp(units.second/(units.ohm*units.farad)))`, root-caused via traceback to unitsystem.py:179, fix applied in

### X10 — What has been investigated about branch dimensionless function

Ground already covered by research on this subject.

- **function_branch_semantics** — In sympy/physics/units/unitsystem.py's _collect_factor_and_dimension, the Function branch (around line 192-196) returns the raw dimension of each argument unchanged instead of checking is_dimensionles
  Looked in: sympy/physics/units/unitsystem.py lines 152-200 (the Function elif branch specifically)
- **non_dimensionless_arg_behaviour** — What should happen for functions like exp/log/sin whose argument is NOT dimensionless (e.g. exp(second))? Does current behaviour raise anywhere, or does it just silently return the wrong (non-collapse
  Looked in: sympy/physics/units/unitsystem.py Function branch, and sympy/functions element-wise (e.g. exp.eval) for any dimension validation
- **multi_arg_and_pow_functions** — How does the fix interact with multi-argument Function instances (e.g. atan2 with two args, one dimensionless and one not) and with Pow-based roots like sqrt — does the existing Pow branch already cor
  Looked in: sympy/physics/units/unitsystem.py Pow branch (167-172) vs Function branch (192-196); check existing tests in sympy/physics/units/tests/test_quantities.py for pr

...and 2 more line(s) of ground covered.### I3 — Fallback approaches for branch dimensionless function

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` fix-function-branch-collapse-dimensionless** — correct_dimension_check_rate unmeasured
  1. Reproduce the issue (judgement)
  2. Locate the defect (judgement)
  3. Apply the fix (judgement)
  4. Verify the repro (judgement)
  5. Run the regression suite (judgement)
  6. Build varied train instances (judgement)
  7. Record trials (judgement)

**`A7` function-branch-collapse-dimensionless-arg** — correct_dimension_check_rate unmeasured
  1. `probe_reproduce_dimension_issue(...)`
  2. `probe_find_call_sites(...)`
  3. Patch the branch to collapse dimensionless args (judgement)
  4. `probe_reproduce_dimension_issue(...)`
  5. `probe_run_pytest_selection(...)`## References

### X11 — Tried: fix-function-branch-collapse-dimensionless

Fix in UnitSystem._collect_factor_and_dimension's `elif isinstance(expr, Function):` branch (sympy/physics/units/unitsystem.py): for each collected arg dimension, collapse to Dimension(1) when self.get_dimension_system().is_dimensionless(d[1]) is True (mirroring the existing Pow branch), then return

**Hypothesis**: The Function branch is the sole handler for generic Function exprs (exp, log, sin, ...) and never normalizes/collapses argument dimensions to Dimension(1) even when semantically dimensionless, unlike the Pow branch just above it which does call is_dimensionless(). This causes downstream Add-branch dimension comparisons to fail structurally (Dimension(1) != Dimension(time/(capacitance*impedance))) 

**Status**: potential (train 9/9). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: collapse-dimensionless-function-and-pow-base

Extends collapse-dimensionless-in-function-branch: in sympy/physics/units/unitsystem.py's _collect_factor_and_dimension, collapse to Dimension(1) both (a) each Function arg's dimension when is_dimensionless (existing fix) and (b) the Pow branch's base dimension when is_dimensionless, before computin

**Hypothesis**: The Function-only fix is right but incomplete: sqrt(x) is represented as Pow(x, 1/2), not Function, so a dimensionless-but-non-1 base dimension flowing through Pow still fails the Add branch's raw != comparison. Collapsing the Pow base the same way the exponent is already collapsed closes this gap. Falsified if the sqrt case still fails after the Pow-branch collapse, or if it breaks any existing u

**Status**: potential (test 1/1, train 2/2). Investigated already — extend this rather than re-deriving it.

### I4 — Steps to solve branch dimensionless function

The steps that solve branch dimensionless function, in order. Run them.

1. `probe_reproduce_dimension_issue(...)` — Reproduce the issue
2. `probe_find_call_sites(...)` — Locate the defect
3. `probe_apply_text_replacement(...)` — Apply the fix
4. `probe_reproduce_dimension_issue(...)` — Verify the repro
5. `probe_run_python_snippet(...)` — Check the sqrt-as-Pow edge case
6. `probe_run_pytest_selection(...)` — Run the regression suite
7. `research_record_trial(...)` — Record trials

## References

### X13 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **correct_dimension_check_rate** (max, target 1.0).

**Established**
- collapse-dimensionless-in-function-branch (working)
- function-branch-dimensionless-check (potential)

**Still open**
- fix-function-branch-collapse-dimensionless (potential)
- fix-add-branch-comparison-logic (potential)
- fix-dimension-or-dimensionsystem-class (potential)
- add-branch-dimensionless-aware-comparison (potential)
- function-branch-collapse-dimensionless-arg (potential)
- add-branch-dimensionless-tolerant-compare (potential)

**Ruled out**
- collapse-dimensionless-function-and-pow-base (failed correct_dimension_check_rate=1.0) — try 1: target tests still failing: tests/checkers/unittest_misc.py::TestFixme::test_non_al
- fix-total-degree-check-in-itermonomials (falsified correct_dimension_check_rate=0.0)

**Where the detail is**
- fix-function-branch-collapse-dimensionless: Investigation of sympy/physics/units/unitsystem.py at base commit 514579c655bf; reproduced via sympy.physics.u
- collapse-dimensionless-in-function-branch: tmp/research/aspect-reproduce.md — manual repro with `SI._collect_factor_and_dimension(100 + exp(units.second/

...and 5 more line(s); see the full record.