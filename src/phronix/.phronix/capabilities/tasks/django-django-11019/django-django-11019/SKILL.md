---
name: django-django-11019
description: What is known about django__django-11019. Nothing yet.
subject: django-django-11019
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify failing media ordering problem |
| `I2` | Instructions | Key idea: Media merge ordering is determined by addition sequence, causing MediaOrderConflictWarning when widgets are added in non‑dependency order |
| `I3` | Instructions | Diagnosis core problem |
| `I4` | Instructions | Attempt-1 failure diagnosis |
| `I5` | Instructions | Key code locations and fix focus |
| `I6` | Instructions | Suppress false MediaOrderConflictWarnings while preserving order |
| `R1` | Rules | Do not alter existing widget Media classes without preserving order dependencies |
| `R2` | Rules | Nothing is established about this subject yet |
| `R3` | Rules | Preserve existing media ordering |

## Instructions

### I1 — Identify failing media ordering problem

When a Django form with multiple widgets defines overlapping JS media files, the combined media may raise MediaOrderConflictWarning due to incorrect ordering, causing target tests to fail.

### I2 — Key idea: Media merge ordering is determined by addition sequence, causing MediaOrderConflictWarning when widgets are added in non‑dependency order

Django merges Media objects by concatenating their js lists in the order widgets are combined. This ordering can conflict with required dependencies, leading to warnings and test failures.

### I3 — Diagnosis core problem

Media order conflict warnings in Django forms when merging JS dependencies from multiple widgets. `merge()` in django/forms/widgets.py:118-150 detects conflicts when same JS path appears in both lists in opposite relative order. `__add__()` at lines 152-156 concatenates `_js_lists` without ordering awareness. Previous attempt produced zero code changes — only analyzed code.

### I4 — Attempt-1 failure diagnosis

Previous attempt (attempt-1) produced zero code changes — agent only read and analyzed django/forms/widgets.py's merge() and __add__() methods without implementing any fix. Error: "agent produced no patch", judged "Resolved: NO". Key findings: exchange.md confirms "agent looked at code but made no changes. The diff was empty." attempt-notes.md: "This attempt did not solve the task. The most valuable thing you can record is why the approach above was insufficient, so the next attempt does not repeat it."

### I5 — Key code locations and fix focus

Key files: django/forms/widgets.py lines 118-156. merge() static method (118-150): walks list_2 in reverse, inserts paths at last_insert_index, raises MediaOrderConflictWarning if index > last_insert_index. __add__() (152-156): simply concatenates self._js_lists + other._js_lists without dependency ordering awareness. Next attempt should: understand JS dependency relationships in widget Media definitions, modify merge()/__add__() to respect ordering so dependent files appear after dependencies, fix should handle overlapping widgets (ColorPicker, SimpleTextWidget, FancyTextWidget) used together.

### I6 — Suppress false MediaOrderConflictWarnings while preserving order

Edit `django/forms/widgets.py`:
1. Locate the `Media.merge` static method.
2. Replace its implementation with:
```python
@staticmethod
def merge(list_1, list_2):
    """Merge two media lists while preserving the intended order.
    If a duplicate file appears, warn **only** when the duplicate in list_2
    would be placed *before* its existing occurrence, indicating an opposite‑order conflict.
    Duplicates that appear after their first occurrence are ignored, preserving the earlier order.
    """
    combined = list(list_1)
    insert_pos = len(combined)
    for path in list_2:
        if path in combined:
            existing_index = combined.index(path)
            if existing_index < insert_pos:
                warnings.warn(
                    f"{path} already appears earlier than insertion point.",
                    MediaOrderConflictWarning,
                )
        else:
            combined.append(path)
            insert_pos += 1
    return combined
```"

## Rules

### R1 — Do not alter existing widget Media classes without preserving order dependencies

When fixing ordering, ensure that any changes maintain the original dependency relationships between js files, otherwise other widgets may break.

### R2 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `django__django-11019`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R3 — Preserve existing media ordering

The Media.merge function must never reorder existing media entries; it may only append new unique entries or ignore duplicates that appear later in the list.

## References

- `skill_load(name="django-django-11019", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
