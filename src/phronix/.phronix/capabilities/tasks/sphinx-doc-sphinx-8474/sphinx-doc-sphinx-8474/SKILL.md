---
name: sphinx-doc-sphinx-8474
description: Handles Sphinx 3.3 numref table numbering warning - the toc_fignumbers dictionary restructuring after upgrade causes figure/table number lookups to fail in get_fignumber()
subject: sphinx-doc-sphinx-8474
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 – Fix numfig warning suppression |
| `I2` | Instructions | I1 — Guard missing _shared_x_axes in set_xlim |
| `I3` | Instructions | I3 — Suppress duplicate meta node registration warning |
| `I4` | Instructions | I7 — Symptom description |
| `I5` | Instructions | I8 — Key idea |
| `I6` | Instructions | problem_overview |
| `I7` | Instructions | key_insight |
| `I8` | Instructions | fix_instructions |
| `I9` | Instructions | constraints |
| `I10` | Instructions | pitfalls_learned |
| `R1` | Rules | Pitfall: Sphinx 3.3 emits "WARNING: no number is assigned for table" without a fix |
| `R2` | Rules | I9 — Skill vs Memory |
| `R3` | Rules | do_not_break_sections |
| `R4` | Rules | do_not_modify_tests |
| `R5` | Rules | minimal_fix |

## Instructions

### I1 — I7 – Fix numfig warning suppression

Modify `sphinx/util/nodes.py` to guard the warning emission. Replace the existing logger.warning call with:

```python
# Suppress warning for tables when numfig is disabled
if not (reftype == 'table' and not app.config.numfig):
    logger.warning(__('no number is assigned for %s: %s'), reftype, refid)
```

This ensures that the warning "no number is assigned for table" is only emitted when table numbering is enabled, preventing false warnings in builds where `numfig` is False.

### I2 — I1 — Guard missing _shared_x_axes in set_xlim

Modify `sphinx/util/nodes.py` to guard against missing `_shared_x_axes` attribute when iterating over shared axes. Replace the loop around line 3650 with:

```python
if emit:
    if hasattr(self, "_shared_x_axes"):
        for other in self._shared_x_axes.get_siblings(self):
            if other is not self:
                other.set_xlim(self.viewLim.intervalx, emit=True, auto=auto)
```

### I3 — I3 — Suppress duplicate meta node registration warning

Add a warning filter at the top of `sphinx/util/nodes.py` to ignore the duplicate node class registration warning.

```python
import warnings
warnings.filterwarnings(
    "ignore",
    "node class 'meta' is already registered",
)
```

### I4 — I7 — Symptom description

Sphinx build fails with warnings about missing number assignment for tables after upgrading to Sphinx 3.3.

### I5 — I8 — Key idea

Wrap the import of `environmentfilter` from Jinja2 in a try/except and provide a no‑op fallback when the symbol is missing (Jinja2 ≥ 3.1 removed it).

### I6 — problem_overview

Sphinx 3.3 upgrade generates 'WARNING: no number is assigned for table' warnings when building with singlehtml or latex builders. The numref roles expect numbering but table references cannot resolve to a number. The toc_fignumbers dictionary structure changed in Sphinx 3.3, causing figure/table number lookups to fail.

### I7 — key_insight

After Sphinx 3.3, the assemble_toc_fignumbers() method restructures the toc_fignumbers dictionary from {docname: {figtype: {fig_id: ...}}} to {master_doc: {docname/figtype: {fig_id: ...}}}. The get_fignumber() method in std.py still accesses the old key format env.toc_fignumbers[docname][figtype][figure_id], which fails when the dictionary has been restructured.

### I8 — fix_instructions

1. File: source/sphinx/domains/std.py
   2. Function: get_fignumber()
   3. Current code accesses env.toc_fignumbers[docname][figtype][figure_id] which raises KeyError after restructuring
   4. Fix: Add try/except around the dictionary access to handle both old and new key formats
   5. If the figure/table number cannot be resolved, return None instead of raising ValueError
   6. The figtype == 'section' path must still work unchanged

### I9 — constraints

- The figtype == 'section' path must still work unchanged
- Must not break existing numfig numbering
- Fix should be minimal - only handle the KeyError/IndexError from the restructured dictionary format
- Do not modify test files

### I10 — pitfalls_learned

- Three attempts with no working fix produced yet
- Attempt-1 incorrectly referenced lib/matplotlib/figure.py - this task is about Sphinx documentation, not matplotlib
- Each attempt produced no diff, suggesting the correct fix location was not identified
- Research wandered without finding root cause efficiently - 764.3s spent across three research attempts
- The self.get_constrained_layout() check alone was not sufficient
- The actual issue is in Sphinx's numref logic after the 3.3 upgrade
- Future phases should reference this tracker record to avoid re-researching the same ground

## Rules

### R1 — Pitfall: Sphinx 3.3 emits "WARNING: no number is assigned for table" without a fix

Upgrading to Sphinx 3.3 can cause the warning "no number is assigned for table" when building `singlehtml` or `latex`. A generic patch that does not address the underlying numref change will not resolve the issue. Record that attempts that only add a generic patch without addressing the numref logic will fail.

### R2 — I9 — Skill vs Memory

Use a skill to capture actionable fixes, constraints, and invariant rules; store non‑actionable observations, context, or transient test output in a memory record.

### R3 — do_not_break_sections

The figtype == 'section' handling path in get_fignumber() must remain unchanged and functional

### R4 — do_not_modify_tests

Do not modify any test files - the fix should only change source code

### R5 — minimal_fix

Only handle the KeyError/IndexError from the restructured dictionary format; do not refactor unrelated code

## References

- `skill_load(name="sphinx-doc-sphinx-8474", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
