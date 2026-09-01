# Lessons — pytest-dev-pytest-5227

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Format change from %(filename)-25s to %(name)s:%(filename)s changes ou

**2026-08-29** — Format change from %(filename)-25s to %(name)s:%(filename)s changes output patterns enough that tests checking exact log output may fail. The 3 target tests were designed to pass with the name-inclusive format, but 34 regression tests may show slightly different output due to reordering and new %(name)s field. Key: add %(name)s for module name but verify both target and regression suites after change.
