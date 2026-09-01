---
name: pylint-dev-pylint-7228-regex-unicode-fix
description: Fix _regexp_validator to support Unicode property escapes like \p{Han} using the regex module with re fallback
subject: pylint config regexp validation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem recognition |
| `I2` | Instructions | Key insight |
| `I3` | Instructions | Fix implementation |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Always use regex module first |
| `R2` | Rules | Fallback to re on ImportError |
| `R3` | Rules | Do not modify test files |
| `R4` | Rules | Keep changes minimal |

## Instructions

### I1 — Problem recognition

When a user configures function-rgx or similar options with Unicode property escapes like \\p{Han} in their .pylintrc, pylint crashes with re.error: bad escape \\p at position 1 because Python's built-in re module does not support Unicode property escapes.

### I2 — Key insight

The _regexp_validator function in pylint/config/option.py uses re.compile() which cannot handle \p{Han} and similar Unicode property escapes. The solution is to use the third-party regex module (which fully supports Unicode property escapes) with a fallback to re if regex is not installed.

### I3 — Fix implementation

1. In pylint/config/option.py, modify the _regexp_validator function (line 23-31)
2. Add try/except ImportError block to import regex module
3. Use regex.compile(value) as primary, fall back to re.compile(value) on ImportError
4. This ensures Unicode property escapes work when regex is available, while maintaining backward compatibility

### I4 — Constraints

- Must not break existing regex validation for standard patterns
- Must gracefully fall back to re if regex module is not installed
- Test files encode the old buggy behavior but must NOT be modified per task rules
- The fix should be minimal and surgical - only change the _regexp_validator function

### I5 — Pitfalls and lessons

- Tests (test_regex_error, test_csv_regex_error) expect the old buggy behavior with backslash - these test expectations encode the bug, not the correct behavior
- The source code fix is correct - it matches Sphinx 2.4.3 behavior as described in the issue
- Earlier attempts that only added try/except around re.compile without switching to regex.compile still failed
- The regex module must be imported inside the function to avoid import errors when it's not installed
- Using regex as primary and re as fallback is the correct approach; reverse order breaks Unicode support

## Rules

### R1 — Always use regex module first

When compiling regex patterns for validation, attempt to use the regex module first as it supports Unicode property escapes like \p{Han}

### R2 — Fallback to re on ImportError

If the regex module is not available (ImportError), fall back to the standard re module to maintain backward compatibility

### R3 — Do not modify test files

Test expectations encode the old buggy behavior; do not modify them per task instructions

### R4 — Keep changes minimal

Only modify the _regexp_validator function in pylint/config/option.py - no other files should be changed
