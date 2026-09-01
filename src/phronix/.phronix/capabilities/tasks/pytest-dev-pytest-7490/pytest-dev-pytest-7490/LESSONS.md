# Lessons — pytest-dev-pytest-7490

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Dynamic add_marker default changed append from True to False broke xfa

**2026-08-29** — Dynamic add_marker default changed append from True to False broke xfail behavior; need to keep append=True for dynamic markers.

### L2 — Dynamic add_marker default broke xfail

**2026-08-29** — I7 — The change to `Node.add_marker` default `append=False` caused xfail tests to fail, specifically `test_dynamic_xfail_set_during_runtest_failed` expecting xfailed but got failed. The fix restores `append=True` and resolves the failure.
