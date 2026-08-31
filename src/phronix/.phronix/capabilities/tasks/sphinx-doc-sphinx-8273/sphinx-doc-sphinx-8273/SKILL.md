---
name: sphinx-doc-sphinx-8273
description: Fix Sphinx documentation build failures due to missing static assets and manpage section directory issues
subject: sphinx-doc-sphinx-8273
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Steps |
| `R1` | Rules | Do not delete existing static files |
| `R2` | Rules | All tests must pass |
| `R3` | Rules | Maintain backward compatibility |

## Instructions

### I1 — Problem

Sphinx documentation build fails with a `FileNotFoundError` for missing static assets and incorrect manpage section handling.

### I2 — Key idea

Adding the required static files and ensuring the builder writes outputs to the correct section directories resolves the build errors.

### I3 — Steps

1. Add the missing static files to a new `static/` directory in the project.
2. In `conf.py`, set `html_static_path = ['static']` (or append if already set) so Sphinx includes these assets.
3. Modify `sphinx/builders/manpage.py`:
   - Import `os` at the top.
   - Before writing each manpage, ensure the section directory exists:
     ```python
     section_dir = path.join(self.outdir, 'man', f'man{section}')
     os.makedirs(section_dir, exist_ok=True)
     ```
   - Change the output path to `path.join(section_dir, targetname)`.
4. Run the Sphinx build (`make html` and `make man`) and verify that the previously missing files are now present and the manpage sections are correctly placed.

## Rules

### R1 — Do not delete existing static files

All existing static files must be preserved.

### R2 — All tests must pass

Ensure the existing test suite continues to pass after changes.

### R3 — Maintain backward compatibility

Changes should remain compatible with older Sphinx versions.
