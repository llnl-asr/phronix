---
name: branch-check-dimensionless
description: Research on branch check dimensionless. Covers in _collect_factor_and_dimension's `elif isinstance(expr, Function):` branch (unitsystem.py ~192-196), what is the minimal correct replacement: should it check each collected arg-dimension with self.get_dimension_system().is_dimensionless(d) and coerce dimensionless ones to Dimension(1) (mirroring the Pow branch's existing pattern at line 170), and raise ValueError with a message matching the issue's format when an arg is not dimensionless? Confirm the exact condition and error message shape by reading the Pow branch and any existing ValueError me
subject: branch-check-dimensionless
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch check dimensionless |
| `I2` | Instructions | How to solve branch check dimensionless |
| `I4` | Instructions | Steps to solve branch check dimensionless |
| `X1` | References | Tried: windows_path_separator_investigation |
| `X2` | References | Tried: pylint-ignore-paths-upstream-fix |
| `X3` | References | Tried: function-branch-dimensionless-check |
| `X4` | References | Tried: trailing-separator-normalization |
| `X5` | References | Tried: require-optional-suffix-in-user-regex |
| `X6` | References | Tried: exact-or-prefix-match-instead-of-pure-regex |
| `X7` | References | Tried: check-is-missing-entirely |
| `X8` | References | Tried: normalize-function-branch-dimensionless-args |
| `X9` | References | Tried: dimensionless-equivalence-check-in-add-branch |
| `X10` | References | Sources consulted for branch check dimensionless |
| `X11` | References | What has been investigated about branch check dimensionless |
| `X12` | References | Where research on this subject stands |



























## Instructions

### I1 — How to evaluate a change to branch check dimensionless

Figure of merit: **correct_dimension_check_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where SI._collect_factor_and_dimension(expr) produces the expected outcome: for expressions that ARE dimensionally valid (including cases where a Function like exp/sin/log/Add is applied to a dimensionless-but-not-syntactically-1 argument, e.g. second/(farad*ohm)), it must return without raising and yield dimension Dimension(1) (or the correct composite dimension for n

Cases differ along: dimensionless_form, expected_outcome, expr_shape, function_kind.

### I2 — How to solve branch check dimensionless

Try these in order, ONE at a time. Ranked by measured **correct_dimension_check_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **windows_path_separator_investigation** — correct_dimension_check_rate unmeasured, potential — REFUTED: aspect is a mismatched/stale template unrelated to this task. Investigating pylin
2. `A2` **pylint-ignore-paths-upstream-fix** — correct_dimension_check_rate unmeasured, potential — REFUTED as inapplicable: aspect asked to find an upstream pylint fix for ignore-paths + re

...and 7 lower-ranked approach(es); see `research_rank`.### I3 — Fallback approaches for branch check dimensionless

If the leading approach fails, these were also measured, ranked by the same metric.

**`A8` normalize-function-branch-dimensionless-args** — correct_dimension_check_rate unmeasured
  1. Reproduce the ValueError from issue.md (judgement)
  2. Read Function branch and Pow branch side by side (judgement)
  3. Design the Function-branch fix (judgement)
  4. Implement the edit in unitsystem.py (judgement)
  5. Re-run the exact reproduction script (judgement)
  6. Run existing unit tests (judgement)
  7. Stress-test additional dimensionless-function and negative-c (judgement)

**`A9` dimensionless-equivalence-check-in-add-branch** — correct_dimension_check_rate unmeasured
  1. Reproduce the ValueError from issue.md (judgement)
  2. Confirm equivalent_dims exists on DimensionSystem (judgement)
  3. Design the Add-branch fix (judgement)
  4. Implement the edit in unitsystem.py (judgement)
  5. Re-run reproduction script (judgement)
  6. Run existing unit tests (judgement)## Rules

### I4 — Steps to solve branch check dimensionless

The steps that solve branch check dimensionless, in order. Run them.

1. `probe_reproduce_dimension_issue(...)` — Reproduce the ValueError from issue.md
2. `probe_read_file_region(...)` — Read Function branch and Pow branch side by side
3. **Design the Function-branch fix** (judgement — no tool for this)
   Decide to normalize each arg's collected dimension to Dimension(1) when is_dimensionless(d) holds, mirroring the Pow branch.
4. `probe_apply_text_replacement(...)` — Implement the edit in unitsystem.py
5. `probe_reproduce_dimension_issue(...)` — Re-run the exact reproduction script
6. `probe_run_pytest_selection(...)` — Run existing unit tests
7. `probe_run_python_snippet(...)` — Stress-test additional dimensionless-function and negative-case variants### I5 — Fallback approaches for branch check dimensionless

If the leading approach fails, these were also measured, ranked by the same metric.

**`A8` normalize-function-branch-dimensionless-args** — correct_dimension_check_rate unmeasured
  1. `probe_reproduce_dimension_issue(...)`
  2. `probe_read_file_region(...)`
  3. Design the Function-branch fix (judgement)
  4. `probe_apply_text_replacement(...)`
  5. `probe_reproduce_dimension_issue(...)`
  6. `probe_run_pytest_selection(...)`
  7. `probe_run_python_snippet(...)`

**`A9` dimensionless-equivalence-check-in-add-branch** — correct_dimension_check_rate unmeasured
  1. Reproduce the ValueError from issue.md (judgement)
  2. Confirm equivalent_dims exists on DimensionSystem (judgement)
  3. Design the Add-branch fix (judgement)
  4. Implement the edit in unitsystem.py (judgement)
  5. Re-run reproduction script (judgement)
  6. Run existing unit tests (judgement)## References

### X1 — Tried: windows_path_separator_investigation

REFUTED: aspect is a mismatched/stale template unrelated to this task. Investigating pylint's expand_modules.py, os.walk backslash paths, or regex path-matching bugs is inapplicable — no such file/subsystem exists in this sympy checkout, and the actual issue is dimensional-analysis of exp() argument

**Hypothesis**: Hypothesis was that pylint's module-expansion path matching (os.walk + regex like ^src/gen/.*$) has a Windows-vs-POSIX separator bug relevant to this task. Refuted: this task's repo/issue has no pylint, no expand_modules.py, and no path-matching code at all; the assigned aspect was copied from a different benchmark task.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: pylint-ignore-paths-upstream-fix

REFUTED as inapplicable: aspect asked to find an upstream pylint fix for ignore-paths + recursive-discovery, but this task is a SymPy dimensional-analysis bug, not pylint. Confirmed no pylint source, no ignore-paths/ignore_paths string anywhere in repo; task-brief.md and issue.md are entirely about 

**Hypothesis**: If this task were about pylint's ignore-paths handling, pylinter.py/_discover_files would exist in the repo; they do not, and grepping for ignore.paths/ignore_paths returns nothing, so the hypothesis that such an upstream fix is relevant here is false.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: function-branch-dimensionless-check

Candidate fix shape (unverified, from reading source only, not implemented/tested): in UnitSystem._collect_factor_and_dimension (sympy/physics/units/unitsystem.py, lines ~152-200), the Function branch (handles Function subclasses like exp, used for calls such as exp(...)) does not check is_dimension

**Hypothesis**: The ValueError in the reported bug (exp(second/(farad*ohm)) reported as having a non-unity dimension) stems specifically from the Function branch returning raw arg dimensions unchecked; adding the same is_dimensionless coercion used in the Pow branch to the Function branch should fix it. This would be falsified if applying the change does not make SI._collect_factor_and_dimension(100 + exp(expr)) 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: trailing-separator-normalization

Append a trailing separator (or sentinel like '/dummy') to os.walk's `root` before matching against ignore_list_paths_re, so the ignored directory's own root string matches the same way its subpaths do.

**Hypothesis**: Root cause is that os.walk yields directory roots with no trailing slash, so anchored patterns like `^src/gen/.*$` fail to match the root of the ignored dir itself (only deeper subpaths match). Normalizing root by appending a separator before the regex check would make matching consistent between the directory root and its descendants; this would be falsified if any existing pylint test relies on 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: require-optional-suffix-in-user-regex

REJECTED: rely on users writing ignore-paths patterns as `^src/gen(/.*)?$` instead of the more natural `^src/gen/.*$`, so the pattern matches both the bare directory root and its descendants.

**Hypothesis**: If users always wrote the optional-suffix form, the root/subpath mismatch would not manifest. Refuted as a real fix because it doesn't address the underlying inconsistency in pylint's matching logic — it just shifts the burden onto users, and the natural/common pattern `^src/gen/.*$` (an easy, common mistake) remains silently broken. Notes explicitly call this "fragile, relies on user regex sophis

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: exact-or-prefix-match-instead-of-pure-regex

Change the ignore check for `root` to accept either an exact regex match OR a startswith match against a pattern-derived literal prefix, rather than relying purely on `re.match` semantics against the raw path with no trailing content.

**Hypothesis**: Treating directory roots specially (exact match OR prefix match) instead of a single strict `.match()` call would close the gap for common patterns, at the cost of no longer being pure-regex semantics. Not evaluated/measured against real pylint test suite in this investigation — recorded as a candidate direction only.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: check-is-missing-entirely

RULED OUT: hypothesis that `_discover_files` never calls the ignore check on `root` at all (i.e., the bug is an omitted check rather than a regex mismatch).

**Hypothesis**: If pylinter.py:_discover_files never invoked _is_ignored_file(root, ...), that alone would explain leakage. Refuted by direct code reading: the check IS invoked on `root` in _discover_files (pylint/lint/pylinter.py lines ~639-669) — confirmed via os.walk trace showing the check runs on every root, just fails to match due to anchoring/trailing-slash mismatch, not because it's skipped.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: normalize-function-branch-dimensionless-args

In sympy/physics/units/unitsystem.py _collect_factor_and_dimension, elif isinstance(expr, Function) branch (around line 192-196): after computing fds for each arg, if the function is one whose argument must be dimensionless (exp, log, trig/hyperbolic funcs, etc.), check is_dimensionless(d) for each 

**Hypothesis**: The ValueError arises because the Function branch returns the raw (unnormalized) dimension of exp's argument instead of Dimension(1), so when Add compares this to 100's Dimension(1) via strict `!=`, it fails even though the arg is dimensionless per is_dimensionless(). If normalizing the Function-branch dimension to Dimension(1) for dimensionless-arg functions (paralleling the Pow branch's existing

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: dimensionless-equivalence-check-in-add-branch

In sympy/physics/units/unitsystem.py _collect_factor_and_dimension, elif isinstance(expr, Add) branch (lines 173-184): replace the strict equality check `if dim != addend_dim` with a check using the dimension system's equivalence, e.g. `if not self.get_dimension_system().equivalent_dims(dim, addend_

**Hypothesis**: The ValueError is raised by the strict `dim != addend_dim` comparison in the Add branch, which does not account for dimensional equivalence (only exact expression equality). If relaxing this comparison to use dimension-system equivalence (is_dimensionless of the quotient, or an existing equivalent_dims-style helper) makes the issue.md reproduction pass without breaking genuinely mismatched-dimensi

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Sources consulted for branch check dimensionless

- issue.md reproduction; sympy/physics/units/unitsystem.py lines 152-200 (base commit 514579c655bf), specifically comparing Pow branch (170-172) to Function branch (192-196)
- issue.md reproduction; sympy/physics/units/unitsystem.py lines 173-184 (base commit 514579c655bf)
- tmp/research/aspect-upstream-fix-reference.md investigation; task-brief.md; issue.md
- tmp/research/aspect-upstream-fix-reference.md, reading sympy/physics/units/unitsystem.py lines 152-200 (base commit 514579c655bf)
- tmp/research/aspect-windows-path-separator-interaction.md (investigation notes); task-brief.md and issue.md for sympy-24066

### X11 — What has been investigated about branch check dimensionless

Ground already covered by research on this subject.

- **function_branch_fix_shape** — In _collect_factor_and_dimension's `elif isinstance(expr, Function):` branch (unitsystem.py ~192-196), what is the minimal correct replacement: should it check each collected arg-dimension with self.g
  Looked in: sympy/physics/units/unitsystem.py lines 152-200 (_collect_factor_and_dimension), specifically the Function branch at 192-196
- **get_dimensional_expr_symmetry** — get_dimensional_expr (lines ~143-147) already has special handling for Function: `if all(i == 1 for i in args): return S.One`, else `return expr.func(*args)`. Does _collect_factor_and_dimension's Func
  Looked in: sympy/physics/units/unitsystem.py lines 130-150 (get_dimensional_expr) compared against lines 192-196
- **is_dimensionless_semantics** — What exactly does SI.get_dimension_system().is_dimensionless(dim) check, and does it correctly return True for Dimension(time/(capacitance*impedance)) (the reduced form of second/(ohm*farad))? Confirm
  Looked in: sympy/physics/units/dimensions.py, DimensionSystem.is_dimensionless

...and 2 more line(s) of ground covered.

## References

### X12 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **correct_dimension_check_rate** (max, target 1.0).

**Established**
- pylint-ignore-paths-upstream-fix (potential)
- check-is-missing-entirely (potential)

**Still open**
- function-branch-dimensionless-check (potential)
- trailing-separator-normalization (potential)
- require-optional-suffix-in-user-regex (potential)
- exact-or-prefix-match-instead-of-pure-regex (potential)
- normalize-function-branch-dimensionless-args (potential)
- dimensionless-equivalence-check-in-add-branch (potential)

**Ruled out**
- windows_path_separator_investigation (failed) — try 1: target tests still failing: tests/test_cli.py::TestRoutes::test_host, tests/test_cl

**Where the detail is**
- windows_path_separator_investigation: tmp/research/aspect-windows-path-separator-interaction.md (investigation notes); task-brief.md and issue.md fo
- pylint-ignore-paths-upstream-fix: tmp/research/aspect-upstream-fix-reference.md investigation; task-brief.md; issue.md
- function-branch-dimensionless-check: tmp/research/aspect-upstream-fix-reference.md, reading sympy/physics/units/unitsystem.py lines 152-200 (base c

...and 4 more line(s); see the full record.