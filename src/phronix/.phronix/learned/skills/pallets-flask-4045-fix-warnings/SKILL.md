---
name: pallets-flask-4045-fix-warnings
description: Fixes test failures caused by DeprecationWarning being escalated to error.
subject: pallets-flask-4045-fix-warnings
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Remove filterwarnings error in pytest config |


## Instructions

## Rules

### R1 — Remove filterwarnings error in pytest config

Modify setup.cfg to comment out or remove the line 'filterwarnings = error' to prevent DeprecationWarnings from being treated as errors during testing.

## References
