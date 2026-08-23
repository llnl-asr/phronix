---
name: binary-file-from
description: Research on binary file from. Covers can Config.from_file accept a file mode parameter to support binary loading; can we modify Config.from_file to accept a mode and pass it to open for tomllib support; update Flask documentation to illustrate using Config.from_file with tomllib and binary mode.. Approaches tried: src/flask/config.py.
subject: binary-file-from
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to binary file from |
| `I2` | Instructions | Add mode parameter to Config.from_file for binary support |
| `X1` | References | Where research on this subject stands |











## Instructions

### I1 — How to evaluate a change to binary file from

Figure of merit: **test_failures** (min, target 0.0).

Measured by: Count of failing tests after applying change

Cases differ along: format.

### I2 — Add mode parameter to Config.from_file for binary support

In `flask/config.py`, modify `Config.from_file` signature to accept an optional `mode` argument (default `'r'`). When `mode` is `'rb'`, open the file with binary mode and pass the binary data to `tomllib.load`. Ensure backward compatibility by preserving existing behavior for text mode.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **pass_target_tests** (max, target 1.0).

**Still open**
- src/flask/config.py (potential)
- aspect not yet answered: aspect1
- aspect not yet answered: aspect2
- aspect not yet answered: aspect3
- aspect not yet answered: add-mode-parameter
- aspect not yet answered: wrapper-binary-load

**Where the detail is**
- src/flask/config.py: benchmark attempt
- full record: research topic `pallets__flask-4992` (via research_status, only if this summary is not enough)