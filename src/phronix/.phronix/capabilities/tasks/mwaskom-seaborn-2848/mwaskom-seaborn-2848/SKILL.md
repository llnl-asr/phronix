---
name: mwaskom-seaborn-2848
description: What is known about mwaskom__seaborn-2848. Nothing yet.
subject: mwaskom-seaborn-2848
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 – Safe pandas option_context for older pandas versions |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | R1 – pandas `mode.use_inf_as_null` is optional |
| `R3` | Rules | Constraints |








## Instructions

### I1 — I1 – Safe pandas option_context for older pandas versions

In `seaborn/_oldcore.py` replace the existing `pd.option_context('mode.use_inf_as_null', True)` block with a safe wrapper that only sets the option when it exists:

```python
def _safe_option_context(**options):
    # Filter out options that pandas does not recognise in the current version
    valid = {k: v for k, v in options.items() if k in pd.describe_option.__code__.co_varnames}
    return pd.option_context(*[item for pair in valid.items() for item in pair])
```

Then change the code around line 1090 to:

```python
with _safe_option_context(mode.use_inf_as_null=True):
    # existing logic that may rely on NaNs being treated as nulls
    ...
```

If the option is not present, the context manager becomes a no‑op, avoiding the `OptionError`. The existing `hue_order` filtering added in the previous attempt remains unchanged and will now be exercised correctly.

### I2 — Problem description

pairplot raises an exception when `hue_order` does not include all hue values; the test expects it to drop missing categories silently.

### I3 — Key idea

Filter the provided `hue_order` to only include categories actually present in the data before further processing, so missing hue values are silently ignored.

### I4 — Instructions to solve it

1. Open `seaborn/axisgrid.py` at the location where `hue_order` is processed (around line 300).\n2. Insert the following code before the existing handling of `hue_order`:\n```python\n# Filter hue_order to only include categories present in the data\nif hue_order is not None:\n    present = set(data[hue].dropna().unique()) if hue is not None else set()\n    hue_order = [c for c in hue_order if c in present]\n```\n3. Save the file and run the relevant tests (`pytest -k test_hue_order`).\n4. Ensure all tests pass; if the pandas `mode.use_inf_as_null` error appears, adjust the pandas version or set the option if required.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `mwaskom__seaborn-2848`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — R1 – pandas `mode.use_inf_as_null` is optional

When running seaborn on pandas ≥1.2.0, the option `'mode.use_inf_as_null'` may not exist. Code must check for its presence before using it. The safe wrapper `_safe_option_context` ensures compatibility across pandas versions.

### R3 — Constraints

- Existing tests unrelated to `hue_order` must continue to pass.
- Do not modify other parts of `axisgrid.py`.
- The fix must not rely on changing pandas configuration; it should work with the current pandas version.
- Preserve original `hue_order` ordering for categories that are present.
- The change must not introduce new warnings or deprecation messages.

## References

- `skill_load(name="mwaskom-seaborn-2848", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

