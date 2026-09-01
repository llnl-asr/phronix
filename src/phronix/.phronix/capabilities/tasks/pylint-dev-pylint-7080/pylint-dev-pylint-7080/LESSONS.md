# Lessons — pylint-dev-pylint-7080

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Unused variable warnings persist after imports fixed

After fixing import errors, the variable `tmp` remained unused, causing a pylint warning. Adding a temporary variable without using it introduces spurious warnings. Ensure all declared variables are either used or removed.

### P2 — Max line length warnings persist

Even after adding type hints, some functions exceeded the configured max‑line‑length, causing pylint warnings. Long lines should be split or the line‑length limit adjusted in `pylintrc` only after confirming they are not essential.

### P3 — `redefined-outer-name` warnings introduced during refactor

Refactoring functions can unintentionally reuse a variable name from an outer scope, triggering `redefined-outer-name`. Rename inner variables or adjust outer definitions to avoid the conflict.

## Lessons
