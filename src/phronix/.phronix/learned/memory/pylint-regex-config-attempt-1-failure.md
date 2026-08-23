---
name: pylint-regex-config-attempt-1-failure
description: Attempt to support \p{Han} in pylint regex and fix CSV regex caused test failures
metadata:
  type: project
---

The attempt to add `__path__` adjustments and modify regex handling in pylint's test utilities did not resolve the underlying issues.

**Why:**
- Python's `re` module does not support Unicode property escapes like `\p{Han}`, leading to `re.error: bad escape \p` in `function-rgx`.
- The CSV regex transformation introduced an invalid pattern causing `re.error: missing ), unterminated subpattern`.

**How to apply:**
- Avoid using `\p{Han}` in pylint configuration; use explicit character ranges or alternative regex that Python supports.
- Ensure CSV regex patterns are syntactically correct and balanced parentheses.
- Future attempts should focus on adapting configuration to Python's regex capabilities rather than expecting `\p` support.
