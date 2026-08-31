# Lessons — pytest-dev-pytest-7220

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — basedir approach: why it failed

**2026-08-29** — basedir parameter with _makepath method insufficient: the _makepath method in FormattedExcinfo only transforms paths when not abspath, but the underlying issue is that co_filename from traceback entries may be an absolute path (e.g., /tmp/pytest-of-root/...) that bestrelpath against invocation_dir cannot properly convert to the expected relative form. Additionally, the nodes.py change passes basedir to excinfo.getrepr() but the test_failure_with_changed_cwd test still shows absolute paths because the test's co_filename is already absolute and rooted in the temp test directory, not the invocation directory. The test_show_wrong_path case fails because the path '../test_path_error.py' is correct relative to the new cwd (ddd/), but the expected behavior requires paths to remain relative to the original invocation directory regardless of fixture chdir.
