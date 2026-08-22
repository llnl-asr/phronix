---
name: degree
description: Research on degree. Covers does itermonomials correctly generate monomials with a given min_degree; are all monomials with total degree in [min,max] produced; is behavior identical when itermonomials is called inside a nested function. Approaches tried: iter degree combinations, max exponent filter.
subject: degree
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to degree |
| `I2` | Instructions | How to solve degree |
| `I3` | Instructions | Steps to solve degree |
| `X1` | References | Tried: iter-degree-combinations |
| `X2` | References | Tried: max-exponent-filter |
| `X3` | References | What has been investigated about degree |
| `X4` | References | Where research on this subject stands |












## Instructions

### I1 — How to evaluate a change to degree

Figure of merit: **missing_monomials** (min, target 0.0).

Measured by: Run a Python snippet that generates monomials using sp.itermonomials with given states, max_degrees, min_degrees, compute the set of all monomials of total degree within bounds via combinatorial enumeration, and count how many expected monomials are missing from the output. The figure of merit is this missing count; lower is better, target 0.

Cases differ along: max_degree, min_degree, nested, variables.

### I2 — How to solve degree

Try these in order, ONE at a time. Ranked by measured **missing_monomials** (min, target 0.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **iter-degree-combinations** — missing_monomials unmeasured, potential — Iterate each degree and generate combos via combinations_with_replacement
2. `A2` **max-exponent-filter** — missing_monomials unmeasured, potential — Filter monomials using max exponent >= min_degree

### I3 — Steps to solve degree

The steps that solve degree, in order. Run them.

1. **Iterate total degrees** (judgement — no tool for this)
   Loop over each total degree from min_degree to max_degree inclusive.
2. **Generate variable combinations** (judgement — no tool for this)
   For each degree, use combinations_with_replacement for commutative variables and product for non‑commutative variables to form tuples of variables.
3. **Construct monomials** (judgement — no tool for this)
   Create monomials by multiplying the variables in each tuple (Mul(*tuple)).
4. **Collect and yield results** (judgement — no tool for this)
   Collect monomials into a set to avoid duplicates and yield them as the final generator.

4 deterministic step(s) have no capability yet: Iterate total degrees, Generate variable combinations, Construct monomials. Build them with `capability_new` rather than doing that work by hand again.

## Rules

## References

### X1 — Tried: iter-degree-combinations

Iterate each degree and generate combos via combinations_with_replacement

**Hypothesis**: Generating monomials by iterating over each total degree from min_degree to max_degree and using combinatorial generation will include all valid monomials, fixing the previous missing cases.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: max-exponent-filter

Filter monomials using max exponent >= min_degree

**Hypothesis**: Using max(powers.values()) >= min_degree will correctly filter monomials for itermonomials.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — What has been investigated about degree

Ground already covered by research on this subject.

- **min_degree_logic** — Does itermonomials correctly generate monomials with a given min_degree?
- **total_degree_enumeration** — Are all monomials with total degree in [min,max] produced?
- **nested_functionality** — Is behavior identical when itermonomials is called inside a nested function?
- **max_greater_than_min** — Does itermonomials handle max_degree > min_degree correctly?

### X4 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **missing_monomials** (min, target 0.0).

**Still open**
- max-exponent-filter (potential)
- (no files changed) (potential)
- src/flask/cli.py (potential missing_monomials=0.0)
- aspect not yet answered: min_degree_logic
- aspect not yet answered: total_degree_enumeration
- aspect not yet answered: nested_functionality

**Ruled out**
- iter-degree-combinations (failed) — try 2: target tests still failing: tests/test_cli.py::TestRoutes::test_host, tests/test_cl

**Where the detail is**
- iter-degree-combinations: Investigation notes aspect-recursive-flag-interaction.md
- max-exponent-filter: Investigation notes aspect-recursive-flag-interaction.md
- (no files changed): benchmark attempt
- src/flask/cli.py: benchmark attempt
- full record: research topic `sympy__sympy-21847` (via research_status, only if this summary is not enough)