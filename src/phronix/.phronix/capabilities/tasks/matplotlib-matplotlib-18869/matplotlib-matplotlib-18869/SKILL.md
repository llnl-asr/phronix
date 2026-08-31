---
name: matplotlib-matplotlib-18869
description: Expose comparable version_info attribute for Matplotlib
subject: matplotlib-matplotlib-18869
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add version_info attribute |
| `R1` | Rules | Preserve existing __version__ behavior |

## Instructions

### I1 — Add version_info attribute

Implement a `__getattr__` case for "version_info" in `lib/matplotlib/__init__.py` that returns a tuple of integer version parts parsed from `__version__`. This should handle non‑numeric segments by stopping at the first non‑integer part.

**Implementation example:**
```python
if name == "version_info":
    ver = __getattr__("__version__")
    parts = ver.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            break
    return tuple(nums)
```

## Rules

### R1 — Preserve existing __version__ behavior

The existing `__getattr__` handling for `__version__` must remain unchanged; do not modify its logic.
