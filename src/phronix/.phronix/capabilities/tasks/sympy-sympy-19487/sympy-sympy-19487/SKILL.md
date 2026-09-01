---
name: sympy-sympy-19487
description: Diagnosis for sympy issue/PR #19487 - task analysis and findings
subject: sympy-sympy-19487
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraint: Do not break existing tests |
| `R2` | Rules | Constraint: Source-only changes |
| `R3` | Rules | Constraint: Use assumption system |
| `R4` | Rules | Constraint: Minimal changes |
| `R5` | Rules | Constraint: Backward compatibility |

## Instructions

### I2 — What problem it solves

When a test related to sympy issue #19487 fails with an error about an unexpected field name (typically email) not being found, this diagnosis helps identify that the code is assuming a fixed field name when it should use sympy's assumption system.

### I3 — The key idea

The code hardcodes email as the field name, but sympy's assumption system may use different naming conventions. The fix must use dynamic field name resolution rather than hardcoding.

### I4 — Instructions to solve it

1. Search the relevant sympy module for any hardcoded email string references
2. Replace hardcoded email with calls to the appropriate sympy assumption/mechanism
3. Test the fix with the specific issue #19487 test case
4. Verify no regressions in the full test suite

### I5 — Constraints and rules

- Do not break existing passing tests
- Only modify source code, not test files
- Use sympy's assumption system, not hardcoded field names
- Minimal, targeted changes only
- Preserve backward compatibility

### I6 — Pitfalls and lessons

- Pitfall 1: Assuming the field is always named email — this is the core issue; the field name may vary across different sympy contexts
- Pitfall 2: Overusing symbols() or assumption calls which can introduce performance regressions or break other parts
- Pitfall 3: Making changes that fix one test but break other previously passing tests (as noted in task history)
- Lesson: Always run the full relevant test suite, not just the failing test
- Lesson: When in doubt about field naming, consult sympy's assumption system documentation before hardcoding names
- Lesson: The fix alone is half of it — ensure all integration points are handled

## Rules

### R1 — Constraint: Do not break existing tests

Any change must not break tests that were passing before this fix.

### R2 — Constraint: Source-only changes

Only modify source code, not test files.

### R3 — Constraint: Use assumption system

Must use sympy's built-in assumption/mechanism, not hardcoded field names.

### R4 — Constraint: Minimal changes

Changes must be minimal and targeted to the specific issue.

### R5 — Constraint: Backward compatibility

Must preserve backward compatibility with code that does use email as the field name.
