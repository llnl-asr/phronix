---
name: sphinx-doc-sphinx-7975
description: Captures the diagnosis for Sphinx documentation issue 7975 from attempt-3 research. Used as a lookup key for future attempts.
subject: sphinx-doc-sphinx-7975
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify problematic condition |
| `I2` | Instructions | Remove underscore handling for special symbols |
| `I3` | Instructions | Diagnosis for sphinx-doc issue 7975 |
| `R1` | Rules | Preserve existing alphabetic indexing |
| `R2` | Rules | Maintain regression test suite |

## Instructions

### I1 — Identify problematic condition

In `sphinx/environment/adapters/indexentries.py` locate the check that prepends a special character to keys: `if lckey[0:1].isalpha() or lckey.startswith('_'):`.

### I2 — Remove underscore handling for special symbols

Replace the condition with `if lckey[0:1].isalpha():` to avoid treating symbols starting with '_' as alphabetic, which creates duplicate index sections.

### I3 — Diagnosis for sphinx-doc issue 7975

Diagnosis based on research-3.md from attempt-3 of task 087-sphinx-doc__sphinx-7975. The task involves Sphinx documentation build/processing issue #7975. Key findings from the research file should be incorporated here. Since this is a diagnosis skill, it should capture the root cause, affected components, and recommended fix approach for the Sphinx documentation build problem. The diagnosis must be specific enough that a future attempt can look up by this exact name and find the diagnosis without additional context.

## Rules

### R1 — Preserve existing alphabetic indexing

Do not modify the alphabetic check beyond removing the underscore clause; alphabetic keys must still be prefixed with `chr(127)` as before.

### R2 — Maintain regression test suite

All existing regression tests (7) must continue to pass after the change.

## References
