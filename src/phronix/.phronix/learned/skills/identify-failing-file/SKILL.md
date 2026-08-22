---
name: identify-failing-file
description: Identify the file causing import error from pytest output
subject: identify-failing-file
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Parse pytest output to locate failing file |


## Instructions

### I1 — Parse pytest output to locate failing file

Given the output from the run_pytest capability, search for lines containing 'ImportError while loading conftest' and extract the file path. The file path will be something like 'tests/conftest.py'. Record that as the source of the failure.

## Rules

## References
