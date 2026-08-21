---
name: pallets
description: Research on pallets. Approaches tried: assertion_blueprint_name_no_dot.
subject: pallets
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pallets |
| `X1` | References | Tried: assertion_blueprint_name_no_dot |
| `X2` | References | Where research on this subject stands |

















## Instructions

### I1 — How to evaluate a change to pallets

Figure of merit: **hidden-test-pass-rate** (max, target 100.0).

Measured by: Run hidden test suite and count number of passed hidden tests

Cases differ along: blueprint_name_type, expected_error, location.

## Rules

## References

### X1 — Tried: assertion_blueprint_name_no_dot

Add assertion in Blueprint.__init__ to reject dot in blueprint name

**Hypothesis**: Raising AssertionError in Blueprint.__init__ prevents usage of blueprint names containing dots, enforcing rule early

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **hidden-test-pass-rate** (max, target 100.0).

**Still open**
- assertion_blueprint_name_no_dot (potential)
- pylint/checkers/misc.py (potential hidden-test-pass-rate=1.0)

**Where the detail is**
- assertion_blueprint_name_no_dot: investigation notes aspect-recursive-flag-interaction
- pylint/checkers/misc.py: benchmark attempt
- full record: research topic `pallets__flask-4045` (via research_status, only if this summary is not enough)