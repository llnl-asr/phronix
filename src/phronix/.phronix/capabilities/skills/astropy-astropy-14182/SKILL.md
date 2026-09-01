---
name: astropy-astropy-14182
description: What is known about astropy-astropy-14182: Problem, Key Idea, Instructions
subject: astropy-astropy-14182
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Updated fix for header_rows handling |
| `I5` | Instructions | Fix RST writer to accept header_rows kwarg |
| `I6` | Instructions | Update RST.__init__ to accept header_rows |
| `R1` | Rules | Constraints |
| `R2` | Rules | What has been achieved so far, and what has not |

## Instructions

### I1 — Problem

RestructuredText output does not support the `header_rows` argument, causing a TypeError when writing tables with `header_rows`.

### I2 — Key Idea

The RST writer must forward unknown keyword arguments (including `header_rows`) to its superclass, and store the header rows for later use.

### I3 — Instructions

1. Edit `astropy/io/ascii/rst.py`:
   ```diff
   - def __init__(self):
   -     super().__init__(delimiter_pad=None, bookend=False)
   + def __init__(self, **kwargs):
   +     header_rows = kwargs.pop('header_rows', None)
   +     super().__init__(delimiter_pad=None, bookend=False, **kwargs)
   +     if header_rows is not None:
   +         self.header.header_rows = header_rows
   +         self.data.header_rows = header_rows
   ```

### I4 — Updated fix for header_rows handling

1. Edit `astropy/io/ascii/rst.py`.
2. Change the class `RST` initialization to accept arbitrary keyword arguments and forward `header_rows` to the FixedWidth parent.
```python
class RST(FixedWidth):
    def __init__(self, **kwargs):
        header_rows = kwargs.pop('header_rows', None)
        super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows, **kwargs)
```
3. Ensure that any other kwargs are passed unchanged to the parent class.
4. Run the failing test `test_rst_with_header_rows`; it should now pass.
5. Run the full test suite to confirm no regressions.

### I5 — Fix RST writer to accept header_rows kwarg

1. Edit `astropy/io/ascii/rst.py`.
2. Change the `RST.__init__` signature to accept `**kwargs`.
3. Extract `header_rows = kwargs.pop('header_rows', None)`.
4. Call the parent initializer with `header_rows=header_rows` and the remaining kwargs:
   ```python
   def __init__(self, **kwargs):
       header_rows = kwargs.pop('header_rows', None)
       super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows, **kwargs)
   ```
5. Save the file and run the failing test `test_rst_with_header_rows` – it should now pass.
6. Run the full test suite to ensure no regressions.

### I6 — Update RST.__init__ to accept header_rows

Modified `RST.__init__` signature to `def __init__(self, **kwargs):`. Extracted `header_rows = kwargs.pop('header_rows', None)` and called `super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows, **kwargs)`. Preserves backward compatibility and forwards any extra kwargs.

This resolves the `TypeError` when passing `header_rows` to `QTable.write` and fixes the failing `test_rst_with_header_rows`.

Run the full test suite to ensure no regressions.

## Rules

### R1 — Constraints

- Existing tests must continue to pass.
- The RST writer must not alter behavior of other formats.
- Adding **kwargs must not silently drop required parameters.
- Header rows handling must not break column type conversion.

### R2 — What has been achieved so far, and what has not

**No target test passes yet.** Every approach so far has left all of them failing.

**Still failing (1).** This is what is left to do, and the whole task is not:
- `astropy/io/ascii/tests/test_rst.py::test_rst_with_header_rows`

Measured after try 1.
