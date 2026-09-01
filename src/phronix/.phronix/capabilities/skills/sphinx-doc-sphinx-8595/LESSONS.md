# Lessons — sphinx-doc-sphinx-8595

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Unrelated html5lib stub

Adding a stub `html5lib/__init__.py` does not contribute to fixing the autodoc issue and only increases repository noise.

### P2 — Incorrect Jinja2 import causing test environment failure

Using `environmentfilter` instead of `pass_context` leads to ImportError, preventing pytest from running.

## Lessons
