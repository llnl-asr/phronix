---
name: django-django-12497-hint-correction
description: Error hint text in related.py for ambiguous M2M relationships: changed ForeignKey to ManyToManyField in the check() method's E334/E335 error guidance. The hint at lines 1312 and 1332 previously told users to use ForeignKey with symmetrical=False for recursive relationships, but this was architecturally incorrect since symmetrical and through are ManyToManyField keyword arguments. The attempt corrected this by changing to ManyToManyField, which is proper for recursive M2M guidance. Key learning: the field-name swap is correct, but tests expected the old text pattern; future work should ensure the hint also properly documents that symmetrical is Django 3.0+ optional for recursive relationships.
subject: django error hint text correction for ambiguous recursive many-to-many relationships
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |

## Instructions

## Rules

## References

- `skill_load(name="django-django-12497-hint-correction", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

