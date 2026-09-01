---
name: pallets-flask-4992
description: Lesson about pandas output from IsotonicRegression affecting CalibratedClassifierCV.
subject: pallets-flask-4992
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Problem description |



## Instructions

### I1 — Problem solved

Config.from_file fails when loading TOML because it opens the file in text mode, but tomllib.load requires a binary file. The test calls Config.from_file with an unexpected keyword 'text'. Adding a `mode` parameter (default 'r') and supporting the legacy `text` alias solves the issue.

### I2 — Problem description

A test calls `Config.from_file` with a `text` keyword argument, but the method only accepted `mode`. The method opened files in text mode, causing `tomllib.load` to fail because it requires a binary file. This skill addresses the mismatch and adds backward‑compatible handling.

## Rules

## References

- `skill_load(name="scikit-learn-isotonic-pandas-output", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

