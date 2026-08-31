# Lessons — sphinx-doc-sphinx-8435

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Missing docutils dependency

**2026-08-29** — Attempt 1 added `sphinx.ext.autodoc` but the import error persisted because `docutils` was not installed. Ensure `docutils` is present before enabling autodoc.

### L2 — Version conflict from extra packages

**2026-08-29** — Attempt 2 introduced extra packages that caused version conflicts, breaking the build. When adding dependencies, ensure compatibility with existing package versions.
