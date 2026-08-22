---
name: pylint-fixme
description: The pylint-fixme subject.
subject: pylint-fixme
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Regex for fixme notes must match end-of-line |


## Instructions

## Rules

### R1 — Regex for fixme notes must match end-of-line

When constructing the fixme regex, use `(?:\b|$)` after the note alternatives to match tags that end the line or string, ensuring punctuation‑only tags are recognized.

## References
