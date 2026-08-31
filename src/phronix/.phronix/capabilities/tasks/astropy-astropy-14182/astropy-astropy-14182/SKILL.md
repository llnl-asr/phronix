---
name: astropy-astropy-14182
description: Fix RST writer to accept header_rows and handle delimiter and bookend
subject: astropy-astropy-14182
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7: Symptom Identification |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | I3: Update configuration.py for nullcontext fallback |
| `I4` | Instructions | I4: Modify RST writer to accept **kwargs |
| `I5` | Instructions | Add constructor to propagate header_rows |
| `I6` | Instructions | Problem |
| `I7` | Instructions | Instructions to Solve |
| `I8` | Instructions | Edit __init__ method |
| `R1` | Rules | Preserve existing behavior |
| `R2` | Rules | Do not change writer interface incompatibly |
| `R3` | Rules | Constraints |

## Instructions

### I1 — I7: Symptom Identification

Failing test `test_rst_with_header_rows` in `astropy/io/ascii/tests/test_rst.py` due to `RST.__init__` not accepting `header_rows` argument.

### I2 — Key Idea

The RST writer inherits from FixedWidth, which already supports `header_rows`. By passing `header_rows` through the RST constructor to the FixedWidth base, the writer can accept the argument without error.

### I3 — I3: Update configuration.py for nullcontext fallback

In `astropy/config/configuration.py`, replace the import line:
```python
from contextlib import contextmanager, nullcontext
```
with:
```python
from contextlib import contextmanager
try:
    from contextlib import nullcontext
except ImportError:
    class nullcontext:
        def __init__(self, enter_result=None):
            self.enter_result = enter_result
        def __enter__(self):
            return self.enter_result
        def __exit__(self, *exc):
            return False
```

### I4 — I4: Modify RST writer to accept **kwargs

In `astropy/io/ascii/rst.py`, change the `RST` class constructor:
```python
def __init__(self):
    super().__init__(delimiter_pad=None, bookend=False)
```
to:
```python
def __init__(self, **kwargs):
    super().__init__(delimiter_pad=None, bookend=False, **kwargs)
```

### I5 — Add constructor to propagate header_rows

In `astropy/io/ascii/rst.py` add `def __init__(self, header_rows=None):
    super().__init__(header_rows=header_rows)
    if header_rows is not None:
        self.header.header_rows = header_rows
        self.data.header_rows = header_rows`

### I6 — Problem

Adding header_rows support to RST writer fails with TypeError and ValueError when reading tables with header_rows.

### I7 — Instructions to Solve

1. Open `astropy/io/ascii/rst.py`.
2. Modify the `RST` class constructor signature to `def __init__(self, header_rows=None):`.
3. Add a docstring explaining the optional `header_rows` parameter.
4. Call the parent `FixedWidth` constructor with `header_rows=header_rows` alongside existing arguments: `super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows)`.
5. Save the file and run the test suite to confirm that `test_rst_with_header_rows` now passes.

### I8 — Edit __init__ method

Modify class RST in astropy/io/ascii/rst.py: change __init__ to accept **kwargs and call super().__init__(**kwargs). Provide defaults for delimiter_pad=None and bookend=False if not supplied.

## Rules

### R1 — Preserve existing behavior

Do not alter other parts of the RST class; ensure default delimiter_pad and bookend remain as before for callers not passing them.

### R2 — Do not change writer interface incompatibly

Any changes must preserve existing RST writer API; new parameters should be optional and backward compatible.

### R3 — Constraints

- Existing functionality of FixedWidth must remain unchanged for other formats.
- The RST writer must continue to produce correct output when `header_rows` is not provided.
- All regression tests (9) must continue to pass.
- The `delimiter_pad` and `bookend` behavior of RST must not be altered.

## References
