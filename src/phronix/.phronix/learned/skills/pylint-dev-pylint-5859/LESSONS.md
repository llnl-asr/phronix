# Lessons — pylint-dev-pylint-5859

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — root-regex-mismatch not reproduced

**2026-08-21** — Hypothesis "os.walk's bare root string (no trailing slash) fails to match ignore-paths regex like `^src/gen/.*$`, so ignored dirs leak through during recursive discovery" is real as an isolated regex fact (`re.match('^src/gen/.*$','src/gen')` -> False, add trailing slash -> True) but did NOT reproduce as an actual pylint bug. Root cause of the non-reproduction: `_discover_files` never checks the ignore-paths regex against its `root` at all — filtering happens downstream in `expand_modules()` against full file paths, not bare directory roots. Live repro (`ignore-paths=^src/gen/.*$` + `--recursive=y`, both plain-dir and package/`__init__.py` src/gen layouts) correctly excluded src/gen/** in the current checkout. Do not re-propose the "add trailing slash before matching root" fix without first finding an actual call site that matches a bare os.walk root — none was found. Unresolved detail if revisited: which exact `_is_in_ignore_list_re` call site excludes the package-root entry 'src/gen' in expand_modules, since the standalone regex check on it is False yet the end-to-end result is still correctly filtered — needs a breakpoint trace, not re-derivation from scratch.
