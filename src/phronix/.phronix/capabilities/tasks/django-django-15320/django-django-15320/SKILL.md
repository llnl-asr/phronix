---
name: django-django-15320
description: The pytest-all-any-error-messages subject.
subject: django-django-15320
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix all()/any() error messages in pytest assertion rewriting |


## Instructions

### I1 — Fix all()/any() error messages in pytest assertion rewriting

Add `all`/`any` handling to assertrepr_compare in util.py.

## ANSWER
Add detection for `op == "all"` and `op == "any"` in the operator handling section of `assertrepr_compare`. When detected, format the iterable's contents using `_format_iterable()` to show actual values in the error message.

## Rules

## References
