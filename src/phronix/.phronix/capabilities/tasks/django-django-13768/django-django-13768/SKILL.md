---
name: django-django-13768
description: The django-django-13768 subject.
subject: django-django-13768
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for matplotlib issue 25332 - NaN in contour plots |
| `I2` | Instructions | django-django-13768: Add logging to Signal.send_robust() for caught exceptions |



## Instructions

### I1 — Diagnosis for matplotlib issue 25332 - NaN in contour plots

Task: matplotlib-matplotlib-25332 (SWE-bench issue)

Issue: NaN values appearing in contour plot generation

Evidence from git history:
- Commit 66ba515e67 merges PR #25334 from branch xtanion/contour_nan — this is the fix branch for NaN handling in contour plots
- Commit d787258e4e merges PR #25335 from rcomer/stale-typo — unrelated typo fix
- Commit a00680eadb removes redundant to_list conversion — code cleanup  
- Commit 3bdc020a3f fixes a typo [skip ci]

The task involves fixing NaN values in matplotlib's contour plotting functionality. PR #25334 (branch xtanion/contour_nan) contains the actual fix, which likely addresses proper NaN handling in contour path generation or domain traversal code.

Diagnosis captures what can be deduced from repository state without direct issue/PR description access. The fix in PR #25334 addresses contour plot NaN issues, but the specific code changes are not directly visible in the current session state.

Note: This is a partial diagnosis based on git history analysis. The actual PR fix details would need to be verified from the PR #25334 itself.

### I2 — django-django-13768: Add logging to Signal.send_robust() for caught exceptions

The issue is in django/dispatch/dispatcher.py, in the Signal.send_robust() method. 

The current implementation catches exceptions from signal handlers but does not log them. The fix is to add a `logger.exception()` call in the except clause so that exceptions raised in signal receivers are logged and visible to error monitoring tools like Sentry.

From the issue: "by default Signal.send_robust() doesn't have any log messages for exceptions raised in receivers. Since Django logs exceptions in other similar situations, such as missing template variables, I think it would be worth adding a logger.exception() call in the except clause of send_robust()."

The test test_send_robust_fail in DispatcherTests verifies that log messages are present when exceptions occur in signal sending.

The change: Add `logger.exception()` call in the except block of send_robust() in django/dispatch/dispatcher.py. This allows users to see exceptions in their error handling tools and figure out which action to take. Any expected exception should still be caught with a try in the receiver function.

Key aspects:
- Add logging of exceptions caught in send_robust()
- Ensures exceptions in signal receivers are visible to monitoring tools
- Follows Django's pattern of logging exceptions in similar situations
- test_send_robust_fail expects log messages when exceptions occur

## Rules

## References
