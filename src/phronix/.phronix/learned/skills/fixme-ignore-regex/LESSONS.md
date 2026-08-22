# Lessons — fixme-ignore-regex

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — append_sep_to_root_before_ignore_check does not work

**Tried**: append_sep_to_root_before_ignore_check

**Hypothesis**: Appending os.sep to root before the ignore-paths/ignore-patterns regex check in _discover_files would fix pylint-dev/pylint#5859. Falsified because the issue is entirely about fixme/--notes regex matching of punctuation-only tags, not file/directory discovery — _discover_files is never invoked in the code path that produces the reported bug.

**Refuted by**: test 1/2, train 1/1. Do not re-propose this without new evidence.

## Lessons
