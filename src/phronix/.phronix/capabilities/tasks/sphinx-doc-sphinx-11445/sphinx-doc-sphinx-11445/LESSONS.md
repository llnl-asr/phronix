# Lessons — sphinx-doc-sphinx-11445

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempt to fix rst_prolog with domain directives by adding `or line

**2026-08-29** — Attempt to fix rst_prolog with domain directives by adding `or line.strip().startswith('..')` to the skip condition in prepend_prolog(). This partial fix did NOT resolve the 2 target tests. The fix introduced a regression risk - while it correctly skips RST directives, it didn't address the core issue of where prolog should be inserted relative to domain directives at the start of documents. The test output shows the prolog ends up at position 0 before `:mod:`, but expected behavior differs. Need to understand the exact test expectations for prolog positioning when domain directives are present.
