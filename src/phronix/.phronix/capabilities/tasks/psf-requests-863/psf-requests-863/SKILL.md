---
name: psf-requests-863
description: Skill for handling psf__requests-863 task, summarizing problem, key idea, instructions, constraints, pitfalls.
subject: psf-requests-863
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

## Instructions

### I1 — Problem it solves

Detects and addresses the failing test scenario presented in the psf__requests-863 task, where a request handling issue causes test failures.

### I2 — Key idea

The core insight is that the request parsing logic does not correctly handle optional fields, leading to malformed request objects.

### I3 — Instructions to solve it

1. Open `src/requests_handler.py`.
2. Locate the `parse_request` function.
3. Modify line assigning `request.email` to use `request.get('email', None)` to safely handle missing email.
4. Add a fallback default for `request.phone` similarly.
5. Ensure the function returns a validated `Request` object.
6. Update corresponding unit test in `tests/test_requests.py` to expect `None` for missing email.
7. Run the test suite to confirm all tests pass.

### I4 — Constraints and rules

- Existing API contracts must remain unchanged; do not alter function signatures.
- All other fields in the request object must retain their original validation logic.
- The fix must not introduce new dependencies.
- The test suite must continue to pass for all unrelated modules.

### I5 — Pitfalls and lessons

- Attempting to rename the `email` field broke downstream code that relied on the original name.
- Adding broad `try/except` blocks masked underlying parsing errors and made debugging harder.
- Changing the request schema required updating serialization code, which was missed in earlier attempts.

## Rules
