---
name: normalize-paths-before-ignore-check-proven
description: The normalize-paths-before-ignore-check approach for pylint-7080 is now PROVEN working
metadata:
  type: lesson
---

**Status update for research approach:** The "normalize-paths-before-ignore-check" hypothesis in [[normalize-ignore-paths]] is now **working** (previously "potential").

**Evidence:** Attempt 1 applied `os.path.normpath()` at both check points (line 79 and line 145 in `expand_modules.py`) and achieved:
- Target tests: 1 of 1 passing (100%)
- Regression tests: 119 of 120 passing (99.2%)
- The one regression failure (`test_generate_toml_config`) is unrelated: a TOMLKit error on `Can't add a table to a dotted key`, not path-related

**Why this works:** Paths like `./src/gen/file.py` won't match `^src/gen/.*$` without normalization. Both initial file loop AND recursive discovery loop need the normalization applied.

**Lesson:** When an ignore-paths bug involves recursive discovery, check EVERY location where paths are compared against ignore patterns, not just one.
