---
name: django-django-13590-resolve-lookup-value
description: Fix resolve_lookup_value to only apply * unpacking for named tuples
subject: django-django-13590-resolve-lookup-value
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | fix-resolve-lookup-value-namedtuple |


## Instructions

### I1 — fix-resolve-lookup-value-namedtuple

When resolve_lookup_value receives a list or tuple containing expressions that need independent resolution, the method must distinguish between named tuples and regular tuples/lists:

1. Named tuples (have _fields attribute) accept *args in their constructor - apply * unpacking to the generator of resolved values
2. Regular tuples/lists accept a single iterable - do NOT apply * unpacking; pass the generator directly

The fix checks hasattr(type(value), '_fields') to detect named tuples and conditionally applies * unpacking only for that case.

Example:
- NamedTuple(*resolved_values) - works with * unpacking
- RegularTuple([resolved_values]) - works without * unpacking

## Rules

## References

- `skill_load(name="django-django-13590-resolve-lookup-value", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

