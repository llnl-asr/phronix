---
name: matplotlib-25332-pickle-failure
description: The matplotlib-25332-pickle-failure subject.
subject: matplotlib-25332-pickle-failure
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Reset alignment groups before aligning labels |
| `R1` | Rules | Align_labels holds weakref causing pickle failure |



## Instructions

### I1 — Reset alignment groups before aligning labels

Add `self._align_label_groups = {"x": cbook.Grouper(), "y": cbook.Grouper()}` at start of `Figure.align_labels` to avoid weakref pickling errors.

## Rules

### R1 — Align_labels holds weakref causing pickle failure

Calling Figure.align_labels() creates alignment groups that retain weakref objects, leading to TypeError: cannot pickle 'weakref.ReferenceType' object. Resetting the alignment groups before alignment avoids the issue.

## References
