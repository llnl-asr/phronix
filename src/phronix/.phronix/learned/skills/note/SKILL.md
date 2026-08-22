---
name: note
description: Research on note. Covers does the parser correctly identify punctuation-only note tags; are punctuation-only notes filtered out by the ignore mechanism. Approaches tried: pylint/checkers/misc.py.
subject: note
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to note |
| `X1` | References | Where research on this subject stands |






































## Instructions

### I1 — How to evaluate a change to note

Figure of merit: **fixme-punctuation-fom** (max, target 1.0).

Measured by: run pylint with --notes on a file containing a punctuation tag and count W0511 warnings for that line

Cases differ along: file_path, note_type.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **target-tests-passed** (max, target 0.0).

**Still open**
- pylint/checkers/misc.py (potential)
- note_normalization (potential)
- punctuation_note_tags (potential)
- aspect not yet answered: validate-1
- aspect not yet answered: tuning-3-used-for-rapid-iteration
- aspect not yet answered: held-out-1

**Where the detail is**
- pylint/checkers/misc.py: benchmark attempt
- note_normalization: analysis based on issue description
- punctuation_note_tags: issue
- full record: research topic `pylint-dev__pylint-5859` (via research_status, only if this summary is not enough)