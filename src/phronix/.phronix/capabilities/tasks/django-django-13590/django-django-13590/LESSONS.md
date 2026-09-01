# Lessons — django-django-13590

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — L1

The * unpacking fix works for named tuples because they accept *args in __new__, but breaks regular tuples and lists that need iterable constructor

### L2 — L2

The type-specific check hasattr(type(value), '_fields') correctly distinguishes named tuples from regular tuples/lists at runtime

### L3 — L3

Blanket * unpacking is refuted — it solves the named tuple case but introduces 5 regressions; type-specific approach passes all 145 regression tests

### L4 — L4

Complex _print_Float modifications in str.py caused TypeError when _mpf_ is tuple; keep float formatting changes separate from query.py fixes
