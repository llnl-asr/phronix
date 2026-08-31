---
name: psf-requests-1963
description: What to record after a task attempt about the psf-requests-1963 redirect method fix
subject: psf-requests-1963
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | problem-it-solves |
| `I2` | Instructions | key-idea |
| `I3` | Instructions | instructions-to-solve |
| `I4` | Instructions | pitfalls-and-lessons |
| `R1` | Rules | constraints-and-rules |






## Instructions

### I1 — problem-it-solves

When Session.resolve_redirects processes a redirect chain starting with POST, if any intermediate response is 303 See Other, the method gets converted to GET but this change is lost on subsequent redirect iterations because the code always copies from the original request rather than the previously modified request.

### I2 — key-idea

The effective method variable used across redirect hops is not always preserved when each loop iteration copies from the original req; it must be updated from prepared_request.method after each step so that subsequent redirects in the chain use the modified method rather than always starting from the original.

### I3 — instructions-to-solve

- File: requests/sessions.py, Class: SessionRedirectMixin, Method: resolve_redirects
- Add method = req.method initialization before the while resp.is_redirect: loop
- Replace unconditional prepared_request = req.copy() with: if 'prepared_request' in locals(): prepared_request = prepared_request.copy() else: prepared_request = req.copy()
- Replace method = req.method inside the loop body with tracking from the modified request
- After each redirect status code handling block and before the loop continues, add method = prepared_request.method to preserve the effective method across iterations
- Ensure the final prepared_request.method = method assignment executes after all redirect rules are applied

### I4 — pitfalls-and-lessons

- Original code always copied from original req on every iteration, so POST→GET for 303 was lost immediately and next redirect iteration would resend original method
- test_mixed_case_scheme_acceptable and test_pyopenssl_redirect failures are pre-existing SSL certificate errors from httpbin.org endpoints - unrelated to redirect method fix, already discounted by benchmark
- test_conflicting_post_params TypeError about callable vs str data parameter is also pre-existing and unrelated to the redirect fix
- The fix only affects redirect method preservation; non-redirect request behavior remains completely unchanged

## Rules

### R1 — constraints-and-rules

- The conditional copy line must be the very first thing inside the while loop body; it must check for prepared_request in locals before falling back to req
- The method = req.method initialization before the loop and the method = prepared_request.method assignment after each iteration are both required; removing either reverts the fix
- The 303→GET, 302→GET, and 301+POST→GET conversion logic must remain untouched
- The 7 target tests that were previously failing must all pass after applying this skill
- All 112 regression tests that were passing before must continue to pass (at most 2 may regress if the skill is incomplete)
- The method variable must track the effective HTTP method across all redirect hops in the chain
- No test files may be modified as part of this skill

## References

- `skill_load(name="psf-requests-1963", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

