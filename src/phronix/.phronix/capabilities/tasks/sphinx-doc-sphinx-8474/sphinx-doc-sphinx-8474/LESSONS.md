# Lessons — sphinx-doc-sphinx-8474

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fallback for missing environmentfilter does not fix numfig warnings

**2026-08-29** — Attempt to patch sphinx/util/rst.py to add fallback for missing jinja2 environmentfilter caused test failures unrelated to the original warning issue; the change did not resolve the numfig warnings and introduced no new functionality.

### L2 — L2 – Generic fallback does not fix numfig warning

**2026-08-29** — L2 – Attempt to suppress numfig warning incorrectly added fallback for missing jinja2 environmentfilter; it did not address the core warning and caused test failures.

**What broke:** The patch to `sphinx/util/rst.py` only added a fallback for `environmentfilter` and left the numfig warning unchanged. Tests still failed with numfig warnings, and the new code introduced import issues.

**Why it matters:** Shows that generic compatibility shims without targeting the actual source of the warning are ineffective and can break unrelated functionality.
