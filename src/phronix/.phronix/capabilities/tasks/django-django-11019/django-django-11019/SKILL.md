---
name: django-django-11019
description: What is known about django__django-11019. Nothing yet.
subject: django-django-11019
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Suppress false MediaOrderConflictWarnings while preserving order |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | Preserve existing media ordering |




## Instructions

### I1 — Suppress false MediaOrderConflictWarnings while preserving order

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

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `django__django-11019`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — Preserve existing media ordering

The Media.merge function must never reorder existing media entries; it may only append new unique entries or ignore duplicates that appear later in the list.

## References

- `skill_load(name="django-django-11019", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

