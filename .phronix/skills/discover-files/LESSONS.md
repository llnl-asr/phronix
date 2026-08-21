# Lessons — discover-files

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — separator-normalization-windows-posix does not work

**Tried**: separator-normalization-windows-posix

**Hypothesis**: Separator normalization (POSIX vs Windows) causes the reported ignore-paths failure. REFUTED: code already exists and handles this at HEAD; the actual bug is the directory-vs-file-suffix pattern mismatch and relative-vs-absolute argument mismatch (see other approaches).

**Refuted by**: test 0/1, train 0/2, validate 0/1. Do not re-propose this without new evidence.

### P2 — switch-match-to-fullmatch does not work

**Tried**: switch-match-to-fullmatch

**Hypothesis**: Possible surprise source: match() vs fullmatch() semantics could cause unintended partial matches. Not refuted outright but explicitly deprioritized/not investigated further — the notes treat this as orthogonal to the actual reported bug (directory-vs-file pattern mismatch, relative-vs-absolute mismatch).

**Refuted by**: test 0/1, train 0/3, validate 0/1. Do not re-propose this without new evidence.

### P3 — expand-modules-redundant-check-theory does not work

**Tried**: expand-modules-redundant-check-theory

**Hypothesis**: If true, _discover_files' directory-root-level ignore check would already exclude everything expand_modules's file-level check would exclude, making the latter dead code for recursively-discovered inputs; false if expand_modules's check still fires and matters for cases discover_files misses.

**Refuted by**: test 0/1, train 0/2, validate 0/1. Do not re-propose this without new evidence.

## Lessons
