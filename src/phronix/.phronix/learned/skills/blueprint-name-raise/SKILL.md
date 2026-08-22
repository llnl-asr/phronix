---
name: blueprint-name-raise
description: Research on blueprint name raise. Covers where in the Flask codebase is the reported behavior produced (which function/module); what is the smallest reproduction of the issue; which existing test(s) cover this area of code and what do they assert. Approaches tried: raise valueerror on dot in blueprint name, raise on register dot in blueprint name.
subject: blueprint-name-raise
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to blueprint name raise |
| `I2` | Instructions | How to solve blueprint name raise |
| `I4` | Instructions | Steps to solve blueprint name raise |
| `R1` | Rules | X1 (raise-valueerror-on-dot-in-blueprint-name) is confirmed working, not potential |
| `R2` | Rules | Fix this in Add `if "." in name: raise ValueError(...)` to Blueprint.__i |
| `R3` | Rules | Fix this in Confirmed by project changelog: CHANGES.rst already contains |
| `X1` | References | Tried: raise-valueerror-on-dot-in-blueprint-name |
| `X2` | References | Tried: raise-on-register-dot-in-blueprint-name |
| `X3` | References | Sources consulted for blueprint name raise |
| `X4` | References | What has been investigated about blueprint name raise |
| `X5` | References | Where research on this subject stands |
































## Instructions

### I1 — How to evaluate a change to blueprint name raise

Figure of merit: **dotted_blueprint_name_rejection_rate** (max, target 1.0).

Measured by: Fraction of held-out instances where constructing flask.Blueprint(name=..., import_name='x') raises ValueError iff name contains a '.', and does not raise for valid non-dotted names (including valid non-ASCII/identifier-like names), measured by instantiating Blueprint directly in a python snippet and checking exception type/message.

Cases differ along: expect_error, name_form, usage_context.

### I2 — How to solve blueprint name raise

Try these in order, ONE at a time. Ranked by measured **dotted_blueprint_name_rejection_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **raise-valueerror-on-dot-in-blueprint-name** — dotted_blueprint_name_rejection_rate 1.000, confirmed — Confirmed by project changelog: CHANGES.rst already contains "Raise an error when blueprin
2. `A2` **raise-on-register-dot-in-blueprint-name** — dotted_blueprint_name_rejection_rate unmeasured, potential — Instead of (or in addition to) validating in __init__, validate in Blueprint.register() (s### I4 — Steps to solve blueprint name raise

The steps that solve blueprint name raise, in order. Run them.

1. `probe_find_call_sites(...)` — Locate the blueprint name validation site
2. `probe_read_file_region(...)` — Diff against base commit to spot scope creep
3. **Judge whether each changed hunk is in scope for the issue** (judgement — no tool for this)
   The issue only asks to raise an error when the BLUEPRINT NAME contains a dot, mirroring the endpoint-name check added in 1.0. Any change to add_url_rule's separate endpoint/view_func dot checks (which
4. `probe_apply_text_replacement(...)` — Ensure Blueprint.__init__ raises ValueError on a dotted name
5. `probe_apply_text_replacement(...)` — Revert any out-of-scope assert-to-ValueError changes in add_url_rule
6. `probe_run_pytest_selection(...)` — Run the blueprint test suite and score### I5 — Fallback approaches for blueprint name raise

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` raise-on-register-dot-in-blueprint-name** — dotted_blueprint_name_rejection_rate unmeasured
  1. `probe_read_file_region(...)`
  2. `probe_find_call_sites(...)`
  3. Add ValueError check in register() (judgement)
  4. `probe_run_pytest_selection(...)`
  5. Compare against A1 (judgement)## References

### X1 — Tried: raise-valueerror-on-dot-in-blueprint-name

In Blueprint.__init__ (src/flask/blueprints.py, right after `self.name = name`), raise ValueError if "." in name, mirroring the existing dot-checks for endpoints/view function names in Blueprint.add_url_rule (lines ~363-366) which use assert. This is where flask upstream actually placed the fix.

**Hypothesis**: Blueprint(name=...) should raise ValueError at construction time when name contains a dot, since dots are now the nesting separator (name_prefix + "." + self.name in Blueprint.register, line ~360). Falsifiable if any currently-passing test constructs a Blueprint with a dotted name and expects it to succeed.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: raise-on-register-dot-in-blueprint-name

Instead of (or in addition to) validating in __init__, validate in Blueprint.register() (src/flask/blueprints.py ~line 265, before `app.blueprints[self.name] = self`), raising ValueError if "." in self.name. This catches the case where `.name` is mutated on an existing instance after construction, a

**Hypothesis**: Validating only at __init__ time misses blueprints whose .name attribute is reassigned post-construction before registration; validating in register() catches the value actually used for nesting. Falsifiable by checking whether any test mutates blueprint.name after construction — if none do, this approach adds no coverage over the __init__-only check and is strictly inferior (extra code, same beha

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for blueprint name raise

- GitHub issue "Raise error when blueprint name contains a dot"; src/flask/blueprints.py Blueprint.__init__ (~line 170) and add_url_rule dot-assert (~line 364) as the precedent pattern from the 1.0 endp

### X4 — What has been investigated about blueprint name raise

Ground already covered by research on this subject.

- **root_cause_location** — Where in the Flask codebase is the reported behavior produced (which function/module)?
- **minimal_repro** — What is the smallest reproduction of the issue?
- **existing_test_coverage** — Which existing test(s) cover this area of code and what do they assert?
- **fix_approach** — What is the smallest correct code change to fix the issue, and what does it risk breaking?
- **related_history** — Is there related prior history (commits, issues, changelog entries) explaining why the current behavior exists?### I3 — Fallback approaches for blueprint name raise

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` raise-on-register-dot-in-blueprint-name** — dotted_blueprint_name_rejection_rate unmeasured
  1. `probe_read_file_region(...)`
  2. `probe_find_call_sites(...)`
  3. Add ValueError check in register() (judgement)
  4. `probe_run_pytest_selection(...)`
  5. Compare against A1 (judgement)## Rules

### R1 — X1 (raise-valueerror-on-dot-in-blueprint-name) is confirmed working, not potential

`X1` was recorded as "potential (no trials recorded yet)". A `tune` stage has since run it and reported it worked. Treat `X1` as the working approach for this subject; `X5`'s "still open" list is stale on this point until it is regenerated.

### R2 — Fix this in Add `if "." in name: raise ValueError(...)` to Blueprint.__i

Add `if "." in name: raise ValueError(...)` to Blueprint.__init__ only; leave add_url_rule's existing assert-based endpoint/view_func dot checks untouched.

Why it holds: The issue only asks for a dot check on the blueprint name at construction, matching the endpoint-name check added in 1.0. A prior attempt additionally converted add_url_rule's pre-existing `assert "." not in endpoint` / `assert "." not in view_func.__name__` into `raise ValueError`, which is out of scope and breaks tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots (it catche

Confirmed on held-out instances (test 1/1, train 2/3, validate 1/1).

### R3 — Fix this in Confirmed by project changelog: CHANGES.rst already contains

Confirmed by project changelog: CHANGES.rst already contains "Raise an error when blueprint names contain a dot. The dot has special meaning for nested blueprints. :issue:`4041`" under Unreleased, matching the __init__-only ValueError check — no changelog entry mentions changing add_url_rule's asser

Why it holds: Same as before, now corroborated by CHANGES.rst rather than only by reading the diff.

Confirmed on held-out instances (test 1/1, train 2/3, validate 1/1).

### I4 — Steps to solve blueprint name raise

The steps that solve blueprint name raise, in order. Run them.

1. `probe_find_call_sites(...)` — Locate the blueprint name validation site
2. `probe_read_file_region(...)` — Diff against base commit to spot scope creep
3. **Judge whether each changed hunk is in scope for the issue** (judgement — no tool for this)
   The issue only asks to raise an error when the BLUEPRINT NAME contains a dot, mirroring the endpoint-name check added in 1.0. Any change to add_url_rule's separate endpoint/view_func dot checks (which
4. `probe_apply_text_replacement(...)` — Ensure Blueprint.__init__ raises ValueError on a dotted name
5. `probe_apply_text_replacement(...)` — Revert any out-of-scope assert-to-ValueError changes in add_url_rule
6. `probe_run_pytest_selection(...)` — Run the blueprint test suite and score

## References

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **dotted_blueprint_name_rejection_rate** (max, target 1.0).

**Established**
- raise-valueerror-on-dot-in-blueprint-name (confirmed dotted_blueprint_name_rejection_rate=1.0)

**Still open**
- raise-on-register-dot-in-blueprint-name (potential)
- src/flask/cli.py (potential dotted_blueprint_name_rejection_rate=2.0)
- aspect not yet answered: root_cause_location
- aspect not yet answered: minimal_repro
- aspect not yet answered: existing_test_coverage
- aspect not yet answered: fix_approach

**Where the detail is**
- raise-on-register-dot-in-blueprint-name: src/flask/blueprints.py Blueprint.register (~line 265-270) and the name_prefix + "." + self.name nesting logic
- src/flask/cli.py: benchmark attempt
- raise-valueerror-on-dot-in-blueprint-name: CHANGES.rst Unreleased section, entry for :issue:`4041`
- full record: research topic `pallets__flask-4045` (via research_status, only if this summary is not enough)