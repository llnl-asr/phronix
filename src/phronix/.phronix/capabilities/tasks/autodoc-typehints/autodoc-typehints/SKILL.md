---
name: autodoc-typehints
description: The autodoc-typehints subject.
subject: autodoc-typehints
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Handle *args and **kwargs in autodoc_typehints description |


## Instructions

## Rules

### R1 — Handle *args and **kwargs in autodoc_typehints description

When generating autodoc_typehints description output, emit a param entry for *args and **kwargs that includes the type annotation (e.g. ``(*int)``) even if the parameter has no explicit description. Do not skip these entries entirely, as their presence is required for the test expectations.

## References
