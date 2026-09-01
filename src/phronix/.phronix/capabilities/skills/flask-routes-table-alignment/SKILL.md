---
name: flask-routes-table-alignment
description: Fix alignment and header expectations when adding a new column to Flask routes table
subject: flask-routes-table-alignment
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify column addition |
| `I2` | Instructions | Update header expectations |
| `R1` | Rules | Never omit new column values in width calculation |

## Instructions

### I1 — Identify column addition

Locate the code adding a new column to the routes table and ensure its width calculation includes the new values.

### I2 — Update header expectations

Adjust test expectations to account for the new column's header and alignment.

## Rules

### R1 — Never omit new column values in width calculation

Column width must be computed using all column values, including any newly added columns.
