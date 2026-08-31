---
name: astropy-astropy-14365
description: File diagnosis for task astropy-astropy-14365 based on available (empty) content
subject: astropy-astropy-14365
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle Docker pull rate limit for astropy task |
| `I2` | Instructions | Naming convention for this skill |
| `I3` | Instructions | Update __repr__ |
| `I4` | Instructions | Problem description |
| `I5` | Instructions | Key idea |
| `I6` | Instructions | Fix regex case-insensitivity in ascii.qdp |
| `I7` | Instructions | Diagnosis for task astropy-astropy-14365 |
| `R1` | Rules | Maintain backward compatibility |
| `R2` | Rules | Maintain existing regex functionality |

## Instructions

### I1 — Handle Docker pull rate limit for astropy task

1. Log into Docker Hub with `docker login` using credentials that provide a higher pull rate limit.
2. If pulling the image fails with a rate‑limit error, add a short wait (e.g., `sleep 60`) and retry the pull up to three times.
3. As a fallback, configure Docker to use an alternative registry mirror (e.g., `registry-1.docker.io`) and pull from there.
4. After a successful pull, proceed with the task as usual.

### I2 — Naming convention for this skill

Use the task identifier as the skill name, e.g., `astropy-astropy-14365`, mirroring the task's repository and issue number for easy lookup.

### I3 — Update __repr__

Modify ResolverMatch.__repr__ to detect isinstance(self.func, functools.partial). If true, construct func_path from self.func.func.__module__ and name, include partial_args=self.func.args and partial_kwargs=self.func.keywords or {} in the string. Return a formatted representation including these and existing fields.

### I4 — Problem description

QDP commands in ascii.qdp files are case‑sensitive in Astropy, causing parsing errors for lower‑case commands like `read serr 1 2`.

### I5 — Key idea

Parsing of QDP commands should be case‑insensitive; the regular expression matching error commands must accept any letter case without triggering deprecation warnings.

### I6 — Fix regex case-insensitivity in ascii.qdp

File: astropy/io/ascii/qdp.py
```diff
@@
-    _command_re = r"READ [TS]ERR(\\s+[0-9]+)+"
-    _command_re = r"(?i)READ [TS]ERR(\\s+[0-9]+)+"
+    # Make QDP error command matching case‑insensitive without deprecation warning.
+    _command_re = r"(?i)READ [TS]ERR(\\s+[0-9]+)+"
```

This uses an inline case‑insensitive flag placed at the start of the pattern, which avoids the DeprecationWarning and allows lower‑case `read serr` commands to be recognised.

### I7 — Diagnosis for task astropy-astropy-14365

Diagnosis: The research-2.md file referenced at $SCRATCH_ROOT/phronix-bench/runs/claude-0829-040235/claude-phronix/tasks/057-astropy__astropy-14365/attempt-2/research-2.md could not be located in the filesystem. The attempt-2 directory contains only cloned astropy repo files with no diagnosis or research content. Per user instruction "take what is there and file it" - the available content is zero, so this diagnosis reflects that the expected source material was absent. No prior diagnosis findings could be extracted or filed from the non-existent research file. The task astropy-astropy-14365 appears to concern fixing a bug where using clf and pyplot.draw() in a RangeSlider on_changed callback blocks widget input, but no diagnosis content was available to document.

## Rules

### R1 — Maintain backward compatibility

When func is not a functools.partial, preserve original representation format.

### R2 — Maintain existing regex functionality

The case‑insensitive regex must continue to match upper‑case commands exactly as before, ensuring that existing upper‑case QDP files still parse correctly.

## References
