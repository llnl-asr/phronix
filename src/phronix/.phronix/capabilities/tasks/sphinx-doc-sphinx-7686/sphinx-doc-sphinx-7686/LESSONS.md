# Lessons — sphinx-doc-sphinx-7686

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The previous fix attempted to import `pass_environment` from Jinja2 an

**2026-08-31** — The previous fix attempted to import `pass_environment` from Jinja2 and alias it as `environmentfilter`. However, the current Jinja2 version does not expose `pass_environment`, leading to an ImportError during test collection and causing the autosummary tests to fail.

**Symptom:** ImportError: cannot import name 'pass_environment' from 'jinja2'.
**Root cause:** Wrong import alias; the correct function provided by Jinja2 is `environmentfilter`.
**Fix:** Replace the faulty import with `from jinja2 import environmentfilter`.

**Tests broken:** `tests/test_ext_autosummary.py::test_autosummary_generate_content_for_module` and `tests/test_ext_autosummary.py::test_autosummary_generate_content_for_module_skipped` continued to fail due to the import error.

### L2 — ImportError from wrong Jinja2 import

**2026-08-31** — **L2** — Attempted fix imported `pass_environment` which does not exist in current Jinja2, causing ImportError and failing autosummary tests.
