---
name: filter-root
description: Research on filter root: in sympy/polys/monomials.py itermonomials, the total_degree branch filters candidate monomials with `if max(powers.values()) >= min_degree`, which uses the MAX single-variable power instead of the SUM (total degree). Fix is sum(powers.values()) in both commutative and non-commutative loops. Canonical copy — degree-padding was a duplicate of this same sympy-21847 itermonomials subject and now points here.
subject: filter-root
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to filter root |
| `I2` | Instructions | How to solve filter root |
| `I4` | Instructions | Steps to solve filter root |
| `X1` | References | Tried: root_path_regex_mismatch (pylint ignore-paths) applied to sympy fix |
| `X2` | References | Tried: sum_not_max_powers_filter |
| `X3` | References | Tried: direct_exponent_generation_total_degree |
| `X4` | References | Sources consulted for filter root |
| `X5` | References | What has been investigated about filter root |
| `X7` | References | Tried: conditional-domain-column-routes-command |
| `X8` | References | Where research on this subject stands |
| `X9` | References | Tried: root_path_regex_mismatch (pylint ignore-paths) applied to sympy fix |
| `X10` | References | Tried: raise_valueerror_on_dot_in_blueprint_name-r1-r2 |
| `X11` | References | Merged duplicate subject: degree-padding |

## Instructions

### I1 — How to evaluate a change to filter root

Figure of merit: **itermonomials_correct_monomial_set_rate** (max, target 1.0).

Measured by: For each corpus instance, call sp.itermonomials(variables, max_degrees, min_degrees=min_degrees) (scalar or list form as specified), collect the result as a set, and compare against the expected set of monomials computed independently.

Cases differ along: commutativity, degree_form, expected_multivar_terms, min_max_relation, num_variables.

### I2 — How to solve filter root

Try these in order, ONE at a time. Ranked by measured **itermonomials_correct_monomial_set_rate** (max, target 1.0).

1. `sum_not_max_powers_filter` (= degree-padding's `fix-sum-not-max-degree-filter`, see X2) — validated (train 3/3, validate 3/3). In both commutative and non-commutative branches of the total_degree case, replace `max(powers.values()) >= min_degree` with `sum(powers.values()) >= min_degree`.
2. `direct_exponent_generation_total_degree` (= degree-padding's `explicit-degree-loop-no-padding`, see X3) — potential, unmeasured.

Note: two unrelated approaches (conditional-domain-column-routes-command, raise_valueerror_on_dot_in_blueprint_name-r1-r2) also appear ranked here — Flask-blueprint content cross-assigned onto this sympy topic, see [[aspect-pylint-contamination#X1]]. Skip them.

### I4 — Steps to solve filter root

1. Read issue.md/task-brief.md to confirm the actual repo/issue (sympy/sympy, itermonomials).
2. Locate itermonomials in sympy/polys/monomials.py (~lines 121-144), both commutative and non-commutative total_degree loops.
3. Change `max(powers.values()) >= min_degree` to `sum(powers.values()) >= min_degree` in both loops (excluding the padding S.One).
4. Verify with a python snippet reproducing the issue's example.
5. Run sympy/polys/tests/test_monomials.py and module doctests for regressions.

## Rules

## References

### X1 — Tried: root_path_regex_mismatch (pylint ignore-paths) applied to sympy fix

REFUTED as applicable: this aspect's brief describes a pylint expand_modules.py ignore-paths regex-anchoring bug, but the sympy-21847 checkout has no expand_modules.py and no os.walk+regex ignore-list code path at all. See [[aspect-pylint-contamination#X1]] for the general cross-topic pattern this is one instance of.

### X2 — Tried: sum_not_max_powers_filter

In sympy/polys/monomials.py itermonomials, total_degree branch (both loops), replace `max(powers.values()) >= min_degree` with `sum(powers.values()) >= min_degree`. Same fix as degree-padding's `fix-sum-not-max-degree-filter`.

**Status**: validated (train 3/3, validate 3/3). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: direct_exponent_generation_total_degree

Rewrite the total_degree branch to generate exponent tuples directly (yield all tuples of length n with min_degree <= sum <= max_degree) instead of filtering a padded combinations_with_replacement. Same idea as degree-padding's `explicit-degree-loop-no-padding`.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Sources consulted for filter root

sympy/polys/monomials.py lines 121-144 (itermonomials, total_degree branch); issue.md example with min_degrees=max_degrees=3.

### X5 — What has been investigated about filter root

- **root_cause_filter_condition** — the total_degree branch filter uses max() where it should use sum() of powers over the real variables (excluding padding S.One).
- **non_commutative_loop_same_bug** — the non-commutative branch (product(variables, repeat=max_degree), same filter) has the identical defect; same fix applies.
- **list_form_branch_correctness** — the separate list-valued max_degrees/min_degrees branch is unaffected; fix should be scoped to the total_degree=True branches only.
- **padding_variable_interaction / existing_test_coverage** — see degree-padding#X4 for the equivalent framing from the duplicate skill; same facts, no new content.

### X7 — Tried: conditional-domain-column-routes-command

Same domain computation as add-domain-column-to-routes-command (src/flask/cli.py routes_command), gated on host_matching/subdomain. Refuted here: this task's actual issue is the sympy itermonomials bug, unrelated to routes_command output — this approach never touches monomials.py. See [[aspect-pylint-contamination#X1]] for the general cross-assignment pattern.

### X8 — Where research on this subject stands

Measured by **itermonomials_correct_monomial_set_rate** (max, target 1.0).

**Established (working)**: sum_not_max_powers_filter / fix-sum-not-max-degree-filter

**Still open**: direct_exponent_generation_total_degree / explicit-degree-loop-no-padding; aspects non_commutative_loop_same_bug, existing_test_coverage

**Off-topic, cross-assigned from other repos (do not re-derive)**: root_path_regex_mismatch (pylint, see X1); conditional-domain-column-routes-command (flask, see X7); raise_valueerror_on_dot_in_blueprint_name variants (flask blueprints, see X9/X10)

### X9 — Tried: root_path_regex_mismatch (pylint ignore-paths) applied to sympy fix

Duplicate statement of X1 (kept for external references pointing at X9): REFUTED as applicable for the same reason — no expand_modules.py or ignore-list-via-regex code exists anywhere in the sympy checkout. See X1 and [[aspect-pylint-contamination#X1]].

### X10 — Tried: raise_valueerror_on_dot_in_blueprint_name-r1-r2

In src/flask/blueprints.py Blueprint.__init__, raise ValueError if "." in name; testing.py: url_parse -> urlsplit; drop the as_tuple kwarg from FlaskClient.open(). Flask blueprint-dot-name content cross-assigned onto this sympy topic — does not apply here. See [[aspect-pylint-contamination#X1]] and [[pallets-flask-4045#R8]] for where this content actually belongs.

### X11 — Merged duplicate subject: degree-padding

degree-padding covered the exact same bug (itermonomials total_degree branch, sympy/polys/monomials.py, max() vs sum() of powers) under different approach names — `fix-sum-not-max-degree-filter` = this skill's `sum_not_max_powers_filter` (X2), `explicit-degree-loop-no-padding` = this skill's `direct_exponent_generation_total_degree` (X3). Kept filter-root as canonical since aspect-pylint-contamination already cross-links to filter-root#X1/X3; degree-padding is now a pointer skill referencing this one.
