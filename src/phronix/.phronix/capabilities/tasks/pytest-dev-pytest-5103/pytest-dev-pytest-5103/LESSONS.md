# Lessons — pytest-dev-pytest-5103

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — No code change produced for iterable unrolling attempt

**2026-08-29** — Attempt to implement iterable unrolling for all/any assertions produced no code change and was judged as not resolved. The approach of adding a new capability failed to generate a diff, indicating missing implementation steps or incorrect tool usage.

### L2 — Pitfall: Config tweaks insufficient

**2026-08-29** — Assuming that changing tox.ini warning filters would fix the assertion rewrite failure was wrong; the failure stems from pytest’s core rewrite logic, not configurable warnings.
