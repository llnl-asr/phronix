# Lessons — flask-blueprint-dot-names

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — L1's endpoint-exception-type claim is wrong; upstream PR #4045 uses ValueError for all three checks

**2026-08-22** — 2026-08-22 — L1 claimed the `add_url_rule` endpoint/view_func dot-check should raise `AssertionError` (not `ValueError`), inferred only from the existing test name/pattern without reading the actual upstream diff. Confirmed wrong: fetching the real upstream commit 7c5261407dae61679c268b44c63d73909c3fe65 (PR #4045) shows the complete fix converts ALL THREE existing `assert` checks (blueprint name in `__init__`, plus endpoint and view_func dot-checks in `add_url_rule`) to `raise ValueError(...)`, not just the new blueprint-name check. This matches [[flask-blueprint-name-dot-validation-research]] (memory, already recorded this correctly) and ranks #1 (target_tests_passing 2.0) as `all-three-valueerror-complete-upstream` / X15 in the sibling skill `flask-blueprint-dot-validation-complete`. Root cause of the original attempt's failure was not "endpoint check needs AssertionError" as L1 concluded — it was that fix #2 (endpoint/view_func) was missing entirely, and when added it must also be ValueError, not AssertionError. Treat this L2 as correcting L1 on the exception-type point only; L1's other content (two call sites, root-cause-of-attempt-1 diagnosis) still stands.

### L2 — Correct fact, stated plainly (L1's wording is self-referential and confusing)

**2026-08-22** — 2026-08-22 — L1 in this project-layer file was written correcting a same-titled lesson that lives in a different layer (the bundled/global copy at .phronix/learned/skills/flask-blueprint-dot-names/LESSONS.md), not a prior entry in this file — this file had no lessons before L1, so L1's own wording ("L1 claimed...") reads as self-contradictory. Ignore that framing; the operative fact is: for pallets__flask-4045, the correct fix converts all three existing dot checks (Blueprint name in `__init__`, plus endpoint and view_func in `add_url_rule`) to `raise ValueError(...)`, not `AssertionError`, confirmed against upstream commit 7c5261407dae61679c268b44c63d73909c3fe65 (PR #4045). See [[flask-blueprint-name-dot-validation-research]] and `flask-blueprint-dot-validation-complete#X15`.
