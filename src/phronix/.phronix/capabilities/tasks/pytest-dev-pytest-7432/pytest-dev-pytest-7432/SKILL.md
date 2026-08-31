---
name: pytest-dev-pytest-7432
description: Fix for pytest-dev-7432: re‑add runxfail guard in skipping.py
subject: pytest-dev-pytest-7432
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Restore runxfail handling in skipping.py |


## Instructions

### I1 — Restore runxfail handling in skipping.py

In `src/_pytest/skipping.py`, reintroduce the runxfail guard to ensure the location‑fix code executes when `--runxfail` is not used. Replace the removed `elif` block with:

```python
if item.config.getoption("runxfail"):
    # When --runxfail is active, preserve original behaviour (do not modify report).
    pass
else:
    # Existing location‑fix logic remains unchanged.
    ... (no change needed)
```

This preserves the intended handling of `--runxfail` while allowing the skip location fix to operate correctly in normal runs.

**Established tests must continue passing** – the fix must not affect the 76 regression tests that already passed.

**Why this form** – the previous removal broke the `elif` chain, causing the location‑fix block to be skipped entirely, leading to the failing XFail test. Restoring an explicit `if` guard restores the control flow without side effects.

## Rules

## References

- `skill_load(name="pytest-dev-7432-solution", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

