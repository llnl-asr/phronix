---
name: pylint-discover-files-ignore
description: Notes that discover_files_ignore_check aspect under topic pallets__flask-5063 is actually about pylint, not Flask — repo mismatch. See [[pylint-dev-pylint-7080]] for the confirmed repro and the canonical anchoring writeups.
subject: pylint-discover-files-ignore
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The bug and fix in _discover_files — theory, later refuted as the reachable cause |
| `R1` | Rules | Topic pallets__flask-5063 has no pylint code — aspect/topic mismatch |
| `R2` | Rules | ignore-paths anchoring depends on invocation path, not repo-root |

## Instructions

### I1 — The bug and fix in _discover_files — theory, later refuted as the reachable cause

In pre-fix `pylint/lint/pylinter.py` `_discover_files` (~line 585-625), during `os.walk`, `_is_ignored_file(root, ...)` is called once per directory but the per-file generator that yields `.py` files from `files` has no `_is_ignored_file` check on `os.path.join(root, file)`. This looked like the root cause of ignore-paths being skipped under `--recursive=y`.

**Superseded:** direct instrumentation in [[pylint-dev-pylint-7080#R1]] and [[pylint-dev-pylint-7080#R3]] showed this gap is not actually reachable as a bug — `expand_modules()`'s own per-file `_is_ignored_file` check (expand_modules.py:78-81) catches these files downstream regardless, so `check()` still excludes them. A simple 2-level reproduction of this exact theory also failed to reproduce on Linux ([[pylint-dev-pylint-7080#I1]]). The confirmed, reachable break is a different mechanism: an absolute-path CLI argument defeats the anchored ignore-paths regex ([[pylint-dev-pylint-7080#I2]]). Do not re-propose the missing-per-file-check as the fix for pylint-7080 without addressing why R1/R3 refuted it.

## Rules

### R1 — Topic pallets__flask-5063 has no pylint code — aspect/topic mismatch

See [[pallets-flask-5063#R4]] for the full, current record of this mismatch (aspect text leaking in from the sibling pylint-dev/pylint-7080 task) and what to do when it recurs. Do not restate the investigation here; that block is the canonical one.

### R2 — ignore-paths anchoring depends on invocation path, not repo-root

Two distinct, confirmed mechanisms — do not restate, link only:
- Absolute-path CLI argument defeats an anchored (relative-style) ignore-paths regex — canonical writeup at [[pylint-dev-pylint-7080#I2]].
- A user regex like `^src/gen/.*$` requires trailing separator+content and so never matches the bare directory root os.walk yields — canonical writeup at [[pylint-discover-files-ignore-paths#R1]].

The earlier version of this block pointed at a `pylint-ignore-paths` skill that does not exist in this library — a dangling reference. Corrected to the two real locations above.
