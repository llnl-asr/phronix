---
name: django-admin-e108-related-fields
description: The django-admin-e108-related-fields subject.
subject: django-admin-e108-related-fields
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Django admin E108 check for related fields in list_display |
| `R1` | Rules | Django admin E108 check for related fields in list_display |



## Instructions

### I1 — Django admin E108 check for related fields in list_display

1. What problem it solves: When user sets `list_display = ["choice"]` in ModelAdmin where "choice" is a ForeignKey, E108 validation passes but admin page rendering fails at runtime with AttributeError. Check and runtime have inconsistent behavior.

2. The key idea: E108 check in _check_list_display_item must identify whether list_display item is a valid related field (ForeignKey with related_model set) and either approve it or raise E108 with clear message, rather than passing validation and failing at runtime.

## Rules

### R1 — Django admin E108 check for related fields in list_display

2. The key idea: The E108 check in _check_list_display_item needs to identify whether a list_display item is a valid related field (ForeignKey with related_model set) and either approve it or raise E108 with a clear message, rather than passing validation and failing at runtime with a cryptic AttributeError.

## References

- `skill_load(name="django-admin-e108-related-fields", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

