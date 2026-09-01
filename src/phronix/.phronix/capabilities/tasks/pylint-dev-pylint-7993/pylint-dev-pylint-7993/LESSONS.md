# Lessons — pylint-dev-pylint-7993

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Custom braces placeholder handling leads to KeyError

Custom braces in --msg-template cause KeyError because unknown placeholders are left but formatting still expects keys like 'categ'. The placeholder substitution was commented out, but write_message still formats the template, leading to failure.

## Lessons

### L1 — I7 – Placeholder handling caused KeyError

**2026-08-29** — I7 – Placeholder handling caused KeyError in TextReporter.write_message, breaking test_template_option_non_existing and test_template_option_with_header. The attempted comment-out of substitution left unknown placeholders, leading to KeyError on formatting.

### L2 — Custom msg-template braces unsupported in newer pylint versions

**2026-08-29** — Using custom braces in message template does not work on pylint 2.12.2 with Python 3.9; the msg-template parser fails to recognize '{"Category"' leading to UserWarning and incorrect output.

Attempted fix produced no diff; approach insufficient.
