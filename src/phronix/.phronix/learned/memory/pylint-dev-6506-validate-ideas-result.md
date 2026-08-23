---
name: pylint-dev-6506-validate-ideas-result
description: Results of validate-ideas stage for pylint-dev__pylint-6506
metadata:
  type: project
---

The previous attempt added a try/except block in `pylint/lint/run.py` to catch `_UnrecognizedOptionError` and exit with code 32, intending to suppress traceback for unrecognized options. However, the change introduced two regressions:

1. `sys` is referenced without being imported, causing an `UnboundLocalError` during normal execution (observed in `test_can_read_toml_env_variable`).
2. The error handling no longer writes the usage message to stderr, so tests expecting `"usage: pylint"` fail (observed in `test_unknown_option_name` and `test_unknown_short_option_name`).

Consequently, the resolve status remains **NO**: target tests 0/2 passed, regression tests 5/6 passed. The approach was incomplete; further revision is needed to correctly import `sys` and ensure the usage message is emitted on unrecognized options.

**Why:** The fix aimed to improve user experience by removing a stack trace but inadvertently broke normal error handling.
**How to apply:** Import `sys` at the top of `run.py` and modify the exception handling to print the usage message to `stderr` before exiting with the appropriate code, mirroring the behavior of other option errors.
