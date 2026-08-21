# Lessons — pylint-dev

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — get_module_files-leaks-then-filtered does not work

**Tried**: get_module_files-leaks-then-filtered

**Hypothesis**: If get_module_files() is blind to ignore_list_re/ignore_list_paths_re, then files under paths matched only by those regexes would end up in expand_modules()'s final result (falsifiable by checking the final `result` list, not just what get_module_files returns internally).

**Refuted by**: test 0/1, train 0/4, validate 0/1. Do not re-propose this without new evidence.

### P2 — fix-in-expand_modules does not work

**Tried**: fix-in-expand_modules

**Hypothesis**: If expand_modules() omits ignore_list_re/ignore_list_paths_re checks on subfiles it discovers, then files under ignored paths would appear in its non-recursive result set (falsifiable by constructing a package with an ignored subdirectory and checking expand_modules() output directly).

**Refuted by**: test 0/1, train 0/4, validate 0/1. Do not re-propose this without new evidence.

## Lessons
