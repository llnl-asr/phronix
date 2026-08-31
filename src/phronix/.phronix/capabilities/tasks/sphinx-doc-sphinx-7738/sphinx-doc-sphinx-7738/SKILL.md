---
name: sphinx-doc-sphinx-7738
description: The sphinx-doc-sphinx-7738-trailing-underscore-fix subject.
subject: sphinx-doc-sphinx-7738
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |
| `I6` | Instructions | Fix trailing underscore escaping in Napoleon extension |

## Instructions

### I1 — Problem

Attribute names ending with an underscore are rendered with an extra backslash in the generated documentation (e.g., `hello_` becomes `hello\_`).

### I2 — Key idea

Do not escape trailing underscores in `_escape_args_and_kwargs`; keep the name unchanged.

### I3 — Instructions

1. Open `sphinx/ext/napoleon/docstring.py`.
2. Locate the method `_escape_args_and_kwargs`.
3. Replace the block handling `if name.endswith('_'):` so it no longer adds a backslash. The result should be:
```python
    def _escape_args_and_kwargs(self, name: str) -> str:
        # Do not escape trailing underscores for attribute names
        if name.endswith('_'):
            # keep the trailing underscore as is
            name = name
        if name[:2] == '**':
            return r'\*\*' + name[2:]
        # other escaping logic unchanged
        ...
```

### I4 — Constraints

All existing tests (29 of 30 regression tests) must continue to pass. The fix must not break handling of other symbols (e.g., `**kwargs`).

### I5 — Pitfalls

- Changing the whole method can unintentionally affect other escape logic.
- Leaving the old backslash addition will cause the original failure.
- Removing the guard entirely can break attributes without trailing underscores.

### I6 — Fix trailing underscore escaping in Napoleon extension

Fix the _escape_args_and_kwargs method in sphinx/ext/napoleon/docstring.py to not escape trailing underscores, matching Sphinx 2.4.3 behavior.

**Change**: In `sphinx/ext/napoleon/docstring.py`, line 322:
- Before: `name = name[:-1] + r'\_'` (strips underscore AND adds backslash escape)
- After: `name = name[:-1]` (just strips the underscore)

This reverts the escaping behavior so that attribute names like `hello_` render as `hello_` in RST output instead of `hello\_` (with visible backslash).

## References

- `skill_load(name="sphinx-doc-sphinx-7738-trailing-underscore-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
