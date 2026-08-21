---
name: setup-cfg
description: Update pytest config
subject: setup-cfg
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add warning ignore |


## Instructions

### I1 — Add warning ignore

Modify filterwarnings to ignore DeprecationWarning.

[tool:pytest]
filterwarnings =
    error
    ignore::DeprecationWarning

## Rules

## References
