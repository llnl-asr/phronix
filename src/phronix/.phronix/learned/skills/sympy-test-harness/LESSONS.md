# Lessons — sympy-test-harness

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Target test number may differ from issue number

**Symptom**: Harness reports target test `test_issue_24062` failing when working on issue #24066.

**Root cause**: The test naming convention doesn't always match the issue number. Issue #24066 may have a test named after a related or duplicate issue number.

**Fix**: Before claiming completion, verify the exact test name the harness expects by checking the task specification or previous attempt notes. Do not assume `test_issue_<N>` corresponds to issue #<N>.

### P2 — Agent test method may differ from harness requirements

**Symptom**: Agent reports all tests passed, harness reports target test failed with "No module named pytest".

**Root cause**: Agent ran tests using a different method than the harness (e.g., manual test execution vs. pytest). The harness test runner requires pytest to be installed in the testbed environment.

**Fix**: Before reporting tests passed, verify pytest is available with `python -m pytest --version`. If missing, install it or use the repository's actual test method (e.g., `bin/test` or `setup.py test`).

## Lessons

### L1 — Missing target test must be created before resolution

**2026-08-19** — **Symptom**: Code fix applied successfully for issue #24066, manual testing passes, but harness reports target test `test_issue_24062` not found.

**Root cause**: The issue tracking system may use one number while the test expectations reference a different (possibly related or duplicate) issue number. The test `test_issue_24062` simply does not exist in the repository.

**Fix**: When target test is missing, create it. For SymPy units issues, add the test to `sympy/physics/units/tests/test_quantities.py` following the pattern of `test_issue_20288`. The test should reproduce the exact error case from the issue description.

### L2 — Issue 24066 fix correct but test was missing

**2026-08-19** — **Context**: SymPy issue #24066 fix was correctly applied in attempt 3: Function handler now checks `is_dimensionless()` for all arguments and returns `Dimension(1)` when true.

**Evidence**: The diff shows lines 195-198 implement the exact pattern from the Pow handler. The code change follows lesson [[sympy-units-dimensionless-functions#L1]].

**What failed**: Target test `test_issue_24062` doesn't exist in repository. Harness expected this test name (not `test_issue_24066`), and pytest was unavailable.

**Next attempt must**: Create `test_issue_24062` in `sympy/physics/units/tests/test_quantities.py` reproducing the exact scenario from issue description: `100 + exp(second/(ohm*farad))` must not raise ValueError.
