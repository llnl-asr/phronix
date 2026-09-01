# Lessons — django-django-14997

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Diagnosis of task django-14997

**2026-08-29** — The task involves fixing issue #14997 in the Django repository. The diagnosis identified that the problem stems from incorrect handling of async database connections in the `django.db.backends.base.base` module, causing failures under certain transaction scenarios. The primary cause is missing `await` on the `close()` coroutine when cleaning up connections, leading to resource leaks and intermittent test failures. A secondary issue is the lack of proper exception handling around the connection close, which masks the root cause.

**Why:** The async connection cleanup was added without updating all call sites, and tests expecting synchronous behavior now hit the async path.

**How to apply:** Ensure all `close()` calls on async connections are awaited, and add appropriate try/except blocks to handle `RuntimeError` that may arise during cleanup. Update related test cases to await the closure and assert proper cleanup.

### L2 — L2 – Failed async close fix

**2026-08-29** — Attempted fix for async connection close was not applied; tests still failing due to missing await on close().
