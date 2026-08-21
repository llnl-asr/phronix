---
name: pallets-flask-4045
description: Flask issue 4045: Blueprint names containing a dot should be rejected since '.' is reserved for nested-blueprint separators.
subject: pallets-flask-4045
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix site: Blueprint.__init__ has no dot-check on name |
| `R1` | Rules | Unconditional dot-check in Blueprint.__init__ breaks legacy test_dotted_names |
| `R2` | Rules | Do not trust attempt-1 notes' captured pytest output for this issue — re-run pytest directly |
| `X1` | References | Reproduce the target test in a matched python3.9+werkzeug<2.1+pytest<7 venv |





## Instructions

### I1 — Fix site: Blueprint.__init__ has no dot-check on name

Blueprint.__init__ in src/flask/blueprints.py sets self.name = name with no validation. No dot-check exists anywhere in the blueprint code path. If the task requires rejecting dotted blueprint names (dots are reserved as the nesting separator), add the validation here — raise on `"." in name` before the assignment.

## Rules

### R1 — Unconditional dot-check in Blueprint.__init__ breaks legacy test_dotted_names

The naive fix in [[pallets-flask-4045#I1]] (raise on "." in name inside Blueprint.__init__) is confirmed to regress an existing test: an unconditional check there breaks the legacy `test_dotted_names` test, in addition to already being insufficient for `test_route_decorator_custom_endpoint_with_dots` (see [[flask-blueprint-dotted-names#R1]]).

**Why:** some existing legacy test path constructs or relies on a Blueprint whose name contains a dot without expecting a raise — an unconditional check has no escape hatch for it.

**How to apply:** do not apply the raw `__init__` dot-check from I1 as-is. Any dot validation must be scoped/conditioned so `test_dotted_names` still passes, and must also cover the `add_url_rule` endpoint case per [[flask-blueprint-dotted-names#R1]]. Treat I1 as falsified for the unconditional form; re-derive the exact condition against both failing tests before reattempting.

### R2 — Do not trust attempt-1 notes' captured pytest output for this issue — re-run pytest directly

On at least one run, attempt-1's saved notes for this topic captured pytest failure output that was truncated/irrelevant to the actual named target test — diagnosing from those notes alone did not work.

**Why:** whatever captured the attempt-1 output truncated it or captured the wrong test's failure, so it looked informative but didn't answer the question asked.

**How to apply:** when diagnosing a failure for pallets-flask-4045, re-run the specific target test directly (see [[pallets-flask-4045#X1]] for the matched venv) rather than relying on attempt-1's saved notes as the source of truth for what failed and why.

## References

### X1 — Reproduce the target test in a matched python3.9+werkzeug<2.1+pytest<7 venv

The pallets__flask-4045 target test reproduces cleanly in a venv matched to the repo's pinned deps: python3.9, werkzeug<2.1, pytest<7. Using a mismatched/newer combination is a plausible source of spurious collection or import errors unrelated to the actual bug.

**How to apply:** when reproducing or verifying a fix for this issue, build/activate a venv pinned to those bounds before running the target test, rather than using whatever default interpreter/deps are on PATH.
