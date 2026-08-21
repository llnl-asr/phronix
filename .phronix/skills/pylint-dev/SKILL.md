---
name: pylint-dev
description: Research on pylint dev.
subject: pylint-dev
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint dev |
| `X1` | References | Where research on this subject stands |





































































## Instructions

### I1 — How to evaluate a change to pylint dev

Figure of merit: **ignored-paths-effectiveness** (min, target 0.0).

Measured by: Run `pylint --recursive=y src/` with the repository's pyproject.toml settings and count the number of messages originating from files that match any `ignore-paths` pattern. The metric is this count; zero indicates perfect respect of ignore-paths.

Cases differ along: expected, match_scope, path_form, pattern_type.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **ignored-paths-effectiveness** (min, target 0.0).

**Still open**
- aspect not yet answered: ignore-paths parsing
- aspect not yet answered: recursive flag interaction
- aspect not yet answered: pattern matching semantics
- aspect not yet answered: path normalization