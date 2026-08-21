---
name: note
description: Research on note. Covers does pylint emit W0511 for punctuation-only notes; does pylint suppress warnings for alphanumeric notes; how does pylint treat notes mixing punctuation and alphanumeric.
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

Figure of merit: **punctuation_note_warnings** (max, target 1.0).

Measured by: Run `pylint --notes='!?.' <file>` and count W0511 warnings for note tags that are solely punctuation. The metric is the number of such warnings emitted; a higher count means the fix works.

Cases differ along: count, location, note_type.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **punctuation_note_warnings** (max, target 1.0).

**Still open**
- aspect not yet answered: punctuation_note_warning
- aspect not yet answered: alphanumeric_note_suppression
- aspect not yet answered: mixed_note_behavior
- aspect not yet answered: location_effect
- aspect not yet answered: multiple_notes_handling