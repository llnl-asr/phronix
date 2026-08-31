---
name: matplotlib-matplotlib-23964
description: Fix TypeError in backend_ps when handling empty lines in text labels
subject: matplotlib-matplotlib-23964
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply fix to backend_ps.py |
| `R1` | Rules | Do not introduce indentation errors |





## Instructions

### I1 — Problem description

A `TypeError: cannot unpack non-iterable NoneType object` occurs in `backend_ps.py` when a PostScript backend processes a multi-line text label that contains an empty line. The error originates from attempting to iterate over `curr_stream` when it is `None`.

### I2 — Key idea

The failure is caused by `curr_stream` being `None`; guard against `None` before appending to `stream`.

### I3 — Apply fix to backend_ps.py

Edit `lib/matplotlib/backends/backend_ps.py`:
1. Locate the block around line 659 where `stream.append(curr_stream)` is called.
2. Replace the existing code with:
```python
if curr_stream:
    stream.append(curr_stream)
```
3. After the loop, ensure the final append is guarded:
```python
if curr_stream:
    stream.append(curr_stream)
```

## Rules

### R1 — Do not introduce indentation errors

Ensure that any added `if` blocks have properly indented bodies; missing indentation leads to IndentationError as seen in the failed patch.

## References
