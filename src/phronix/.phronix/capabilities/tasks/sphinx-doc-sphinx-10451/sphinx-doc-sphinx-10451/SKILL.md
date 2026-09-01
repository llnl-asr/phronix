---
name: sphinx-doc-sphinx-10451
description: Diagnosis of units display in summarize_variable for task sphinx-doc-sphinx-10451
subject: sphinx-doc-sphinx-10451
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis of units display in summarize_variable |
| `I2` | Instructions | Diagnosis for Sphinx documentation task 10451 |



## Instructions

### I1 — Diagnosis of units display in summarize_variable

The summarize_variable function in formatting.py (line 277-302) supports units via var.attrs.get("units", None). However, the issue is that front_str construction at lines 287-298 adds the units to the display string, but the subsequent max_width calculation at line 299 (values_width = max_width - len(front_str)) correctly accounts for the added units. The core problem revealed was that while units ARE being captured and displayed in the repr output, there was a test failure showing that units in variable attributes were not being propagated to the one-line summary display. The summarize_variable function checks var.attrs at line 295 but the repr flow may not be calling it with variables that have units set, or the units attribute path is not being traversed correctly from the DataArray/Variable objects in the task's test cases. Fix: verify the exact path units take from the test's input objects through summarize_variable, and ensure units from var.attrs["units"] are always included in the front_str when present.

### I2 — Diagnosis for Sphinx documentation task 10451

Task sphinx-doc-sphinx-10451: Sphinx documentation issue. This is attempt-3 of the task. No prior diagnosis exists for this exact task ID. The repository is a Sphinx documentation project with .rst files, themes, and build configuration. Based on the task pattern (sphinx-doc-sphinx-XXXX), this involves a Sphinx documentation bug or feature request. Diagnose the issue and document findings for the next attempt to build upon.

## Rules

## References
