---
name: matplotlib-matplotlib-23987
description: The matplotlib-matplotlib-23987 subject.
subject: matplotlib-matplotlib-23987
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Statement |
| `I2` | Instructions | Key Idea |



## Instructions

### I1 — Problem Statement

The target test `test_set_constrained_layout[False-False]` fails because `Figure.get_constrained_layout()` returns `True` even when a figure is created with `constrained_layout=False`, leading to a UserWarning and test failure.

### I2 — Key Idea

The figure initialization incorrectly forces `constrained_layout=True` regardless of the argument, so the fix must ensure the flag is respected during Figure construction.

## Rules

## References
