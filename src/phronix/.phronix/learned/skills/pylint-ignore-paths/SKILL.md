---
name: pylint-ignore-paths
description: The pylint-ignore-paths subject.
subject: pylint-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Normalize paths and use search for ignore-path regex |


## Instructions

## Rules

### R1 — Normalize paths and use search for ignore-path regex

When checking ignore-path patterns, convert file paths to forward‑slash form, compute a path relative to the cwd, and use `Pattern.search` instead of `match`. This makes regexes work consistently for any location and ensures `ignore-paths` is respected in `--recursive=y` runs.

## References
