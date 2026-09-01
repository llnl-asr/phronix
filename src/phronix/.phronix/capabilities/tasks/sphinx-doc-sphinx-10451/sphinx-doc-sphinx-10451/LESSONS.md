# Lessons — sphinx-doc-sphinx-10451

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Duplicate type fields for *args/**kwargs caused test failures

**2026-08-29** — Attempt 2 failed because duplicate type fields were still generated for *args and **kwargs in autodoc typehints. The test `test_autodoc_typehints_description_with_documented_init` and related tests expected no type annotation for these variadic arguments, but the code added a type field, causing mismatched output.

The fix is to adjust the condition in `modify_field_list` to skip adding a type field when the argument name is 'args' or 'kwargs'. This change resolves the failures for `test_autodoc_typehints_description_*`.
