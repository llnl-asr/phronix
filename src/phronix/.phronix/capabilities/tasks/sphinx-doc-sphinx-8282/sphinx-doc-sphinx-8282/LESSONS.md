# Lessons — sphinx-doc-sphinx-8282

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Incorrect import alias

Using `pass_context` without aliasing to `contextfunction` will break code expecting the original name.

### P2 — Missing Jinja2 version compatibility

If the environment uses an older Jinja2 version lacking `pass_context` or `pass_environment`, the fix will fail; ensure Jinja2 is updated or provide a shim.

## Lessons
