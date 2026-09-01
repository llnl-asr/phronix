# Lessons — psf-requests-2317-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — [{"title": "test_requests_history_is_saved still fails after fix", "bo

**2026-08-31** — [{"title": "test_requests_history_is_saved still fails after fix", "body": "After changing `method = builtin_str(method)` to `method = to_native_string(method)` on line 428 of requests/sessions.py, 7 of 8 target tests passed. However, test_requests_history_is_saved still failed. The fix correctly handles bytes-to-string conversion (str(b'GET') → 'GET' instead of 'b\\'GET\\''), but one test remains unpassed. This may indicate additional code paths or test setup issues that are not directly related to the bytes conversion bug. The pre-existing test failures (SSL cert errors, conflicting post params, mixed case scheme, pyopenssl redirect, stream timeout) remain unrelated to this fix.", "kind": "lesson"}]
