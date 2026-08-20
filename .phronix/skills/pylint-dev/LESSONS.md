# Lessons — pylint-dev

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — ignore-paths-relative-absolute-anchor-mismatch does not work

**Tried**: ignore-paths-relative-absolute-anchor-mismatch

**Hypothesis**: If ignore-paths silently fails to ignore nested/relative paths, it's because _is_in_ignore_list_re uses Pattern.match (anchors only at start) rather than Pattern.search, combined with _discover_files passing os.walk's root (in whatever relative/absolute form the CLI arg had) unmodified. This would be falsified by finding that the actual reported bug reproduces even with a pattern anchored correctl

**Refuted by**: test 0/1, validate 0/1. Do not re-propose this without new evidence.

### P2 — rename-self.config.ignore_paths-to-self._ignore_paths-at-line-604 does not work

**Tried**: rename-self.config.ignore_paths-to-self._ignore_paths-at-line-604

**Hypothesis**: Hypothesis under test: changing self.config.ignore_paths to self._ignore_paths at pylinter.py:604 is the minimal correct fix for the --recursive=y ignoring ignore-paths bug. Falsified by: (1) tracing attribute lifecycle shows _ignore_paths unset at call time (AttributeError), (2) even when set later it is value-identical to config.ignore_paths, so no behavior changes.

**Refuted by**: test 0/1, train 0/6, validate 0/3. Do not re-propose this without new evidence.

## Lessons
