---
name: pylint-discover-files-ignore-paths
description: Notes that discover_files_ignore_check aspect under topic pallets__flask-5063 is actually about pylint, not Flask — repo mismatch. See [[pylint-dev-pylint-7080]] for the confirmed repro and the canonical anchoring writeups.
subject: pylint-discover-files-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Don't retry CLI end-to-end repro in this shared environment without checking for stale parallel-attempt pylint installs first |
| `R1` | Rules | Trailing-content regexes (e.g. `^dir/.*$`) don't match bare directory roots |
| `X1` | References | fix-discover-files-match-root-with-trailing-sep is also a pylint/flask topic mismatch |


## Instructions

### I1 — Don't retry CLI end-to-end repro in this shared environment without checking for stale parallel-attempt pylint installs first

An attempt to verify the single-file-CLI-arg case end-to-end (actual `pylint somefile.py` invocation) failed with unrelated import/version errors — traced to a broken/stale pylint install in the shared machine environment that picked up a DIFFERENT attempt directory's checkout, not a real bug repro. If this needs re-verifying, first confirm which pylint package `python -m pylint` / `pylint` on PATH actually resolves to (e.g. `python -c "import pylint; print(pylint.__file__)"`) before trusting CLI-level results, or invoke via `PyLinter()` API-level calls the way this investigation did.

## Rules

### R1 — Trailing-content regexes (e.g. `^dir/.*$`) don't match bare directory roots

os.walk yields `root` without a trailing separator+content, so a user's ignore-paths regex like `^src/gen/.*$` (needs `/` plus ≥1 more char to satisfy `.*`) does NOT match the bare string `src/gen` — confirmed via re.search/re.match. It DOES match `src/gen/badfile.py`. So checking _is_ignored_file only against `root` silently misses directories whose regex assumes trailing path content, compounding the file-path-never-checked bug. Checking individual file paths (not just root) subsumes this failure mode for files, since the same regex matches full file paths fine — no separate root-matching fix is needed once file-path checking is added.

Also confirmed as a second, independent instance of the same class of break: the identical relative pattern matches when pylint is invoked with a relative directory arg but matches nothing when invoked with an absolute directory arg on identical directory contents — see [[pylint-dev-pylint-7080#I2]] for that reproduction. Both are anchored-regex-vs-actual-path-form mismatches; this block covers the directory-suffix case, pylint-dev-pylint-7080#I2 covers the absolute-path case.

## References

### X1 — fix-discover-files-match-root-with-trailing-sep is also a pylint/flask topic mismatch

The approach fix-discover-files-match-root-with-trailing-sep (see [[discover-files#X50]]) targets pylint/lint/pylinter.py, but was reported under topic pallets__flask-5063 — the Flask repo, which has no pylint/ directory at all. Same class of cross-task mismatch already tracked for this skill's subject and for [[pylint-ignore-paths#R1]] (repeatedly mis-assigned to pallets__flask-5063 and sympy__sympy-24066). Don't apply pylint-specific approaches when the active topic is flask-5063.
