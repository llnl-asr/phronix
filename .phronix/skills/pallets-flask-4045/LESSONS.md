# Lessons — pallets-flask-4045

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — probe_run_pytest_selection fails in this env via PluggyTeardownRaisedWarning, separate from the fix

On py3.13.2 + pytest 7.3.0 in this env, `probe_run_pytest_selection` itself fails: conftest triggers an `ast.Str` DeprecationWarning that surfaces as `PluggyTeardownRaisedWarning` during test teardown, aborting the run before any real assertion. This is the same environment/version-skew class as [[pallets-flask-4045#R6]] (pytest broadly broken here), but specific to how that probe tool's own selection mechanism reacts to the warning — not evidence about the candidate fix. Fall back to manual `python -c` reproduction per R6 rather than trusting this probe's pass/fail here.

## Lessons
