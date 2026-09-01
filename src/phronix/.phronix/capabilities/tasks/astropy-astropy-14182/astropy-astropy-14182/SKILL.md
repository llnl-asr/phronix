---
name: astropy-astropy-14182
description: What is known about astropy__astropy-14182. Nothing yet.
subject: astropy-astropy-14182
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | Constraints and rules |






## Instructions

### I1 — Problem

RST writer does not accept the `header_rows` argument, causing `QTable.write(format="ascii.rst", header_rows=[...])` to raise `TypeError: RST.__init__() got an unexpected keyword argument 'header_rows'` and the corresponding read operation fails with a value conversion error.

### I2 — Key idea

The RST writer must accept and forward the optional `header_rows` argument to its FixedWidth base class, enabling header row handling in both write and read operations.

### I3 — Instructions to solve it

1. Edit `astropy/io/ascii/rst.py`.
2. Change `def __init__(self):` to `def __init__(self, **kwargs):`.
3. Inside, extract `header_rows = kwargs.pop('header_rows', None)`.
4. Call `super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows, **kwargs)`.
5. Save the file and run the failing test `test_rst_with_header_rows`; it should now pass.
6. Run the full regression suite to ensure no other tests break.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `astropy__astropy-14182`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — Constraints and rules

- The change must preserve existing RST output for tables without `header_rows`; all existing regression tests must continue to pass.
- `header_rows` should be optional; passing None must behave exactly as before.
- The `header_rows` argument must be forwarded unchanged to the FixedWidth base class, which already handles it.
- No other signature of `RST.__init__` may be altered; only add `**kwargs` handling.
- The fix must not affect the reading path: `RST.__init__` receives the same kwargs during `QTable.read`.

## References
