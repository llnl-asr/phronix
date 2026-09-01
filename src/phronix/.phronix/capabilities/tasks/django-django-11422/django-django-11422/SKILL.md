---
name: django-django-11422
description: The django-numberformat-empty-string-fix subject.
subject: django-django-11422
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | add-none-and-empty-string-guards |


## Instructions

### I1 — add-none-and-empty-string-guards

Add two guard clauses at the start of the format() function body after the docstring to handle None and empty string inputs, returning "" in both cases. This prevents IndexError when str_number[0] is accessed on an empty string.

## Rules

## References
