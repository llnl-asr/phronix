---
name: sympy-12419
description: The sympy-12419 subject.
subject: sympy-12419
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Summary |
| `I2` | Instructions | Apply Import Fix |
| `R1` | Rules | Compatibility Rule |




## Instructions

### I1 — Problem Summary

Evaluating the total sum of all elements of an identity matrix returned 0 instead of the expected dimension `n`.

### I2 — Apply Import Fix

Edit `sympy/core/basic.py`: replace line `from collections import Mapping` with `from collections.abc import Mapping`.

## Rules

### R1 — Compatibility Rule

Import abstract base classes from `collections.abc` for Python >=3.3; avoid importing `Mapping` from `collections` which is deprecated and removed in Python 3.10.

## References
