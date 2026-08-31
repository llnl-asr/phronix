---
name: matplotlib-matplotlib-24265
description: Compatibility alias added but test still fails due to missing seaborn-bright style
subject: matplotlib-matplotlib-24265
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add missing seaborn style aliases |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Fix steps |
| `I5` | Instructions | Key insight |
| `R1` | Rules | Constraints |
| `R2` | Rules | seaborn-style-name-mapping |

## Instructions

### I1 — Add missing seaborn style aliases

Update `lib/matplotlib/style/core.py` to include legacy seaborn style keys `seaborn-bright` and `seaborn-colorblind` as aliases for the new style names `seaborn-v0_8-bright` and `seaborn-v0_8-colorblind`. This ensures the deprecated styles raise the appropriate deprecation warning and are available for existing code.

```diff
@@
-                "seaborn",
-                "seaborn-bright",
-                "seaborn-colorblind",
+                "seaborn",
+                # Legacy aliases for deprecated seaborn styles (Matplotlib 3.6+)
+                "seaborn-bright", "seaborn-v0_8-bright",
+                "seaborn-colorblind", "seaborn-v0_8-colorblind",
```

### I2 — Problem description

The failing test `test_deprecated_seaborn_styles` expects a deprecation warning for the removed style `seaborn‑bright` and accesses `seaborn‑colorblind`, which is missing in Matplotlib 3.6.1.

### I3 — Key idea

Map deprecated seaborn style names to their v0_8 equivalents and ensure the style registry includes all deprecated entries.

### I4 — Fix steps

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

### I5 — Key insight

The test failure is due to missing deprecation handling for the removed style `seaborn‑bright`, not the missing `seaborn‑colorblind` alias.

## Rules

### R1 — Constraints

- Do not modify other existing style entries.
- Preserve backward compatibility for existing aliases.
- Ensure all existing regression tests (16) continue to pass.
- The deprecation shim must emit MatplotlibDeprecationWarning exactly as expected.

### R2 — seaborn-style-name-mapping

When using `plt.style.use("seaborn-colorblind")` or other old-style seaborn style names, matplotlib fails because the library only registers new-style names with `seaborn-v0_8-` prefix. The `fix_style()` nested function in `lib/matplotlib/style/core.py` transforms old-style names to new-style by replacing `seaborn-` with `seaborn-v0_8-`, but this transformation may not be reaching or being applied correctly for all style names. Test `test_deprecated_seaborn_styles` in `lib/matplotlib/tests/test_style.py` verifies backward compatibility expects `mpl.style.use("seaborn-bright")` to work. Previous attempts modified `use()` and `fix_style()` functions but test still returned 0/1 target tests, possibly due to matplotlib loading from system install rather than repo via PYTHONPATH.

## References

- `skill_load(name="matplotlib-matplotlib-24265", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
