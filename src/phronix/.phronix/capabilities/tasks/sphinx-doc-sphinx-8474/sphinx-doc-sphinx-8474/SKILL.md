---
name: sphinx-doc-sphinx-8474
description: Handles Sphinx 3.3 numref table numbering warning - the toc_fignumbers dictionary restructuring after upgrade causes figure/table number lookups to fail in get_fignumber()
subject: sphinx-doc-sphinx-8474
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | problem_overview |
| `I2` | Instructions | key_insight |
| `I3` | Instructions | fix_instructions |
| `I4` | Instructions | constraints |
| `I5` | Instructions | pitfalls_learned |
| `R1` | Rules | do_not_break_sections |
| `R2` | Rules | do_not_modify_tests |
| `R3` | Rules | minimal_fix |

## Instructions

### I1 — problem_overview

Sphinx 3.3 upgrade generates 'WARNING: no number is assigned for table' warnings when building with singlehtml or latex builders. The numref roles expect numbering but table references cannot resolve to a number. The toc_fignumbers dictionary structure changed in Sphinx 3.3, causing figure/table number lookups to fail.

### I2 — key_insight

After Sphinx 3.3, the assemble_toc_fignumbers() method restructures the toc_fignumbers dictionary from {docname: {figtype: {fig_id: ...}}} to {master_doc: {docname/figtype: {fig_id: ...}}}. The get_fignumber() method in std.py still accesses the old key format env.toc_fignumbers[docname][figtype][figure_id], which fails when the dictionary has been restructured.

### I3 — fix_instructions

1. File: source/sphinx/domains/std.py
   2. Function: get_fignumber()
   3. Current code accesses env.toc_fignumbers[docname][figtype][figure_id] which raises KeyError after restructuring
   4. Fix: Add try/except around the dictionary access to handle both old and new key formats
   5. If the figure/table number cannot be resolved, return None instead of raising ValueError
   6. The figtype == 'section' path must still work unchanged

### I4 — constraints

- The figtype == 'section' path must still work unchanged
- Must not break existing numfig numbering
- Fix should be minimal - only handle the KeyError/IndexError from the restructured dictionary format
- Do not modify test files

### I5 — pitfalls_learned

- Three attempts with no working fix produced yet
- Attempt-1 incorrectly referenced lib/matplotlib/figure.py - this task is about Sphinx documentation, not matplotlib
- Each attempt produced no diff, suggesting the correct fix location was not identified
- Research wandered without finding root cause efficiently - 764.3s spent across three research attempts
- The self.get_constrained_layout() check alone was not sufficient
- The actual issue is in Sphinx's numref logic after the 3.3 upgrade
- Future phases should reference this tracker record to avoid re-researching the same ground

## Rules

### R1 — do_not_break_sections

The figtype == 'section' handling path in get_fignumber() must remain unchanged and functional

### R2 — do_not_modify_tests

Do not modify any test files - the fix should only change source code

### R3 — minimal_fix

Only handle the KeyError/IndexError from the restructured dictionary format; do not refactor unrelated code
