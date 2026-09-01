# Lessons — sympy-sympy-23191

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pretty printing init interferes with vector output

**2026-08-29** — Disabling pretty printing via init_printing(pretty_print=False) changes vector pretty output and causes test_issue_23058 to fail. The test expects default pretty printing behavior.

### L2 — L2 — init_printing disables required pretty printing for vector test\n

**2026-08-29** — L2 — init_printing disables required pretty printing for vector test\n\n**2026-08-29** – The previous fix added `init_printing(pretty_print=False)` in `sympy/vector/__init__.py`. This changed the pretty output of vectors, causing `test_issue_23058` to fail. The test expects the default pretty printing behavior. The fix should remove the import and call to preserve default behavior.\n\n**Impact:** Test suite regression in `sympy/vector/tests/test_printing.py::test_issue_23058`.\n\n**Cost:** 1 edit, ~1 minute.

### L3 — L3 — Removing init_printing caused test_issue_23058 failure

**2026-08

**2026-08-29** — L3 — Removing init_printing caused test_issue_23058 failure

**2026-08-29** — The previous fix added `init_printing(pretty_print=False)` in `sympy/vector/__init__.py`. This changed the default pretty printing of vectors, causing `test_issue_23058` to fail because the test expects the default pretty‑printing order. The fix is to delete the import and call to restore the original behavior.

**Impact:** Regression in `sympy/vector/tests/test_printing.py::test_issue_23058`.
**Cost:** 1 edit, ~1 minute.
