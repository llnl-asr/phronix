# Lessons — sympy-sympy-12419

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls and lessons

P1: Do not run broad test suites (full project test battery) as the primary verification method. The first attempt spent ~1888s / 24 steps re-running unrelated test suites against the correct two-line fix, wasting tokens. Narrow targeted tests covering the affected code paths (matrix symbol manipulation, assumption/refinement with orthogonal matrices, summation of matrix elements under assumptions) are sufficient and much faster. A failing test outside the area you touched was most likely failing before you started; the benchmark measures pre-existing failures separately and discounts them, so do not chase one and do not revert a correct fix because of one.

P2: Do not skip the import relocation. The root cause is importing `MutableMapping`, `defaultdict` from `collections` (not `collections.abc`), and `Mapping` from `collections` (not `collections.abc`), and `Callable` from `collections` (not `collections.abc`). In Python 3.3+, these names exist only in `collections.abc`; the bare `collections` namespace provides only a legacy alias. Skipping this move leaves the hashability check broken, and the total sum of elements collapses to 0 under the orthogonal assumption.

L1: The fix (moving 3 imports to `collections.abc`) is minimal — only 3 lines across 3 files — but it is essential. The previous attempt correctly identified and applied this fix in a single diff, but then wasted ~1888s re-running broad test suites instead of narrow targeted tests. Future attempts should apply the 3-line fix and verify with targeted tests only.

## Lessons
