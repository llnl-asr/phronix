---
name: ignore
description: Research on ignore. Covers does the ignore type (ignore_paths vs ignore_glob) affect which files are excluded; does the ignore pattern apply recursively into subdirectories. Approaches tried: pylint/checkers/misc.py.
subject: ignore
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to ignore |
| `X1` | References | Where research on this subject stands |










## Instructions

### I1 — How to evaluate a change to ignore

Figure of merit: **failed_target_tests** (min, target 0.0).

Measured by: run hidden target tests and count failures

Cases differ along: depth, ignore_type.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **failed_target_tests** (min, target 0.0).

**Still open**
- pylint/checkers/misc.py (potential)
- aspect not yet answered: regex_fix_punctuation_tags
- aspect not yet answered: extend_fixme_pattern_punctuation
- aspect not yet answered: use_notes_rgx_option

**Where the detail is**
- pylint/checkers/misc.py: benchmark attempt
- full record: research topic `pylint-dev__pylint-5859` (via research_status, only if this summary is not enough)