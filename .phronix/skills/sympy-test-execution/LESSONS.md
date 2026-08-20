# Lessons — sympy-test-execution

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Do not invoke pytest directly — module not installed in testbed env

Symptom: running tests with `pytest ...` fails with `No module named pytest`, and the attempt gets judged as 0/N target tests passing even though the code change may be correct.
Root cause: the `testbed` conda env (`/opt/miniconda3/envs/testbed/bin/python`) does not have pytest installed. Sympy has its own test runner.
Fix: run tests via sympy's bundled runner instead, e.g. `python -m sympy.testing.runtests <path>` or `bin/test <path>` or `python -c "import sympy; sympy.test('sympy/polys/tests/test_monomials.py')"`. Verify the runner works before trusting any red/green result — a fix that never actually ran the test suite cannot be judged as failing on merit.

## Lessons
