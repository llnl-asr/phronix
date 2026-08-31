---
name: pytest-dev-pytest-6116
description: Fix CalibratedClassifierCV broadcasting error when transform_output='pandas'
subject: pytest-dev-pytest-6116
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | Add -C shortcut for --collect-only |
| `I7` | Instructions | Detect pandas output |
| `I8` | Instructions | Add domain column to Flask routes CLI |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | Handle dataframe predictions |

## Instructions

### I1 — Problem it solves

Adds a short option for `--collect-only` without breaking existing pytest argument parsing.

### I2 — Key idea

The `-C` short flag collides with pytest’s internal parsing; use a non‑conflicting short flag or register the option explicitly.

### I3 — Instructions to solve it

1. Open `src/_pytest/main.py`.
2. In `pytest_addoption`, replace the added short flag `"-C"` with an unused one, e.g. `"-Z"`.
3. Ensure the new flag is added before other options:
```diff
@@ -107,6 +107,7 @@ def pytest_addoption(parser):
     group = parser.getgroup("collect", "collection")
     group.addoption(
-        "-C",
+        "-Z",
         "--collectonly",
         "--collect-only",
         action="store_true",
```

### I4 — Constraints and rules

- Do not alter existing long options.
- Preserve all regression tests (must stay green).
- The new short flag must not be already used by pytest (avoid `-c`, `-h`, etc.).

### I5 — Pitfalls and lessons

- Adding `-C` caused argument parsing to treat `--collect-only` as `--co`, breaking target tests.
- Always verify short flag uniqueness with pytest’s parser before committing.
- Changing parser behavior without updating help output can confuse users.

### I6 — Add -C shortcut for --collect-only

In src/_pytest/main.py, add a short option `-C` alongside `--collectonly` and `--collect-only`:
```
group.addoption(
    "-C",
    "--collectonly",
    "--collect-only",
    action="store_true",
    help="Only collect tests, do not run them",
)
```

### I7 — Detect pandas output

Check if sklearn.set_config(transform_output) is set to 'pandas' before calling CalibratedClassifierCV.predict_proba.

### I8 — Add domain column to Flask routes CLI

1. Edit `src/flask/cli.py`:
   - Add a new click option `--co` to `routes_command` signature.
   - When `--co` is true, compute a `Domain` column using the rule's subdomain and app's `SERVER_NAME`.
   - Adjust headers, widths, and row formatting to include the `Domain` column.
   - Print the table with the new column when `--co` is supplied.
2. Ensure existing behavior remains unchanged when `--co` is not used.
3. Add appropriate docstring explaining the new flag.
4. Update imports if necessary and run the test suite to confirm no regressions.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pytest-dev__pytest-6116`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — Handle dataframe predictions

Convert dataframe predictions to numpy array before assigning to proba matrix.

## References
