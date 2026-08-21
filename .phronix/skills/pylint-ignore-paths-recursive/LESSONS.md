# Lessons — pylint-ignore-paths-recursive

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --recursive=y ignores ignore-paths: fix in _is_ignored_file

**2026-08-20** — Symptom: `pylint --recursive=y` does not honor `ignore-paths` regex patterns from config, while non-recursive runs do.

Root cause: `_is_ignored_file` in pylint/lint/expand_modules.py matches `ignore_list_paths_re` only against `element` as passed in (e.g. `src\gen\about.py` on Windows or a path with mixed/non-normalized separators). The recursive module-expansion path constructs `element` differently than the non-recursive path, so it never matches the user's regex which assumes normalized `/`-style paths.

Fix (verified, makes the target test pass): add a second match attempt against `os.path.normpath(element)`:
```python
norm_path = os.path.normpath(element)
return (
    basename in ignore_list
    or _is_in_ignore_list_re(basename, ignore_list_re)
    or _is_in_ignore_list_re(element, ignore_list_paths_re)
    or _is_in_ignore_list_re(norm_path, ignore_list_paths_re)
)
```
This is a minimal, targeted fix — one added line plus the norm_path computation. No other files need changes for this bug.
