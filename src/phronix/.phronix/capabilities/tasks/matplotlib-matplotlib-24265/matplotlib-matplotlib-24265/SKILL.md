---
name: matplotlib-matplotlib-24265
description: Compatibility alias added but test still fails due to missing seaborn-bright style
subject: matplotlib-matplotlib-24265
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key insight |
| `I3` | Instructions | Fix steps |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

The failing test `test_deprecated_seaborn_styles` expects a deprecation warning for the removed style `seaborn‑bright` and accesses `seaborn‑colorblind`, which is missing in Matplotlib 3.6.1.

### I2 — Key insight

The test failure is due to missing deprecation handling for the removed style `seaborn‑bright`, not the missing `seaborn‑colorblind` alias.

### I3 — Fix steps

1. In `lib/matplotlib/style/core.py` modify `reload_library` to add a deprecation shim:
   ```python
   if 'seaborn-bright' not in library:
       library['seaborn-bright'] = library.get('seaborn-v0_8-bright')
       _deprecate_style('seaborn-bright')
   ```
   where `_deprecate_style(name)` emits `MatplotlibDeprecationWarning`.
2. Ensure the shim is called during style reload.
3. Update the `available` list accordingly and sort.
4. Add corresponding entry for `seaborn-colorblind` alias if still missing.
5. Run the test suite; `test_deprecated_seaborn_styles` should now emit the expected deprecation warning and pass.

## Rules

### R1 — Constraints

- Do not modify other existing style entries.
- Preserve backward compatibility for existing aliases.
- Ensure all existing regression tests (16) continue to pass.
- The deprecation shim must emit MatplotlibDeprecationWarning exactly as expected.

## References

- `skill_load(name="matplotlib-matplotlib-24265", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

