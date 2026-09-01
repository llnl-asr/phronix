---
name: astropy-astropy-6938
description: Fix exponent separator handling in FITS_rec and adjust test expectations for D exponent format.
subject: astropy-astropy-6938
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update exponent replacement in FITS_rec |
| `I2` | Instructions | Adjust test expectations for D exponent format |
| `R1` | Rules | Preserve existing functionality |
| `R2` | Rules | Do not alter other parts of FITS handling |

## Instructions

### I1 — Update exponent replacement in FITS_rec

In `astropy/io/fits/fitsrec.py`, change the line `output_field.replace(encode_ascii('E'), encode_ascii('D'))` to `output_field = output_field.replace(encode_ascii('E'), encode_ascii('D'))` so the replacement is applied.

### I2 — Adjust test expectations for D exponent format

Modify the expected checksum value in `astropy/io/fits/tests/test_checksum.py` to match the new output `'51IDA1G981GCA1G9'` and update any other assertions that rely on the previous exponent format.

## Rules

### R1 — Preserve existing functionality

All existing regression tests (11 total) must continue to pass.

### R2 — Do not alter other parts of FITS handling

Only the exponent replacement line should be changed; other code in `fitsrec.py` must remain unchanged.
