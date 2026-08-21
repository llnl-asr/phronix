---
name: sympy-sympy-24066
description: The sympy-sympy-24066 subject.
subject: sympy-sympy-24066
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Root cause is in _collect_factor_and_dimension |
| `R1` | Rules | All pylint-family aspects (non_recursive_reference_behavior, upstream_fix_reference, discovery_ignore_check_scope, root_path_regex_mismatch, windows_path_separator_interaction) are misassigned to this topic |
| `X4` | References | Real bug location and shape: UnitSystem._collect_factor_and_dimension Function branch |
| `X6` | References | This topic's pylint-aspect mismatches are an instance of a general pattern |
| `X7` | References | Confirmed pylint bug mechanism: os.walk root lacks trailing slash, breaks anchored ignore-paths regex |













## Instructions

### I1 — Root cause is in _collect_factor_and_dimension

The bug lives in `unitsystem.py`'s `_collect_factor_and_dimension`. Use `probe_reproduce_dimension_issue` to confirm the exact failure mode there before proposing a fix.

## Rules

### R1 — All pylint-family aspects (non_recursive_reference_behavior, upstream_fix_reference, discovery_ignore_check_scope, root_path_regex_mismatch, windows_path_separator_interaction) are misassigned to this topic

None of these five aspect names apply to sympy__sympy-24066. They all describe pylint's `expand_modules()`/`_discover_files()`/ignore-paths machinery (`pylint/lint/expand_modules.py`, `pylint/lint/pylinter.py`) — but this topic's checkout is sympy/sympy 1.12 (base commit 514579c655bf), not pylint. No `expand_modules.py`, no `pylinter.py`, no `pylint/` package, no ignore-paths concept exists anywhere in this checkout (confirmed repeatedly via grep/find).

Why: the aspect-generation step produced these five names for a different (pylint) topic and misdispatched them onto sympy__sympy-24066. Forcing a mapping onto sympy would fabricate findings.

How to apply: if any of these five aspects is (re)assigned here, immediately flag the mismatch rather than re-deriving the same negative grep/find result each time. Ground work instead in the real issue: `SI._collect_factor_and_dimension()` failing to recognize a dimensionless exponent — see [[sympy-sympy-24066#X4]]. This is one instance of a general cross-topic bug — see [[aspect-pylint-contamination#R1]].

## References

### X4 — Real bug location and shape: UnitSystem._collect_factor_and_dimension Function branch

Issue: `SI._collect_factor_and_dimension()` fails to recognize that an exponent/function-argument is dimensionless when wrapped in a Function like `exp`. Reproduction: `exp(units.second/(units.ohm*units.farad))` inside `100 + exp(expr)` raises ValueError claiming a non-unity Dimension, even though `is_dimensionless` on that same dimension returns True when checked directly.

Location: `sympy/physics/units/unitsystem.py`, `UnitSystem._collect_factor_and_dimension`, roughly lines 152-200 (as of base commit 514579c655bf). `Quantity._collect_factor_and_dimension` in `sympy/physics/units/quantities.py:198` is just a deprecated shim forwarding to it — not where to fix.

Mechanism: the `Pow` branch already guards correctly — it computes `exp_dim` for the exponent, checks `self.get_dimension_system().is_dimensionless(exp_dim)`, and coerces `exp_dim = 1` if so, before using it in `dim ** (exp_factor * exp_dim)`. The `Function` branch (which handles any sympy `Function` call, including `exp(...)`) has no equivalent check — it just collects `(factor, dim)` for each arg via recursive calls and returns the raw per-arg dimensions as the dimension of the whole function application, with no dimensionless verification or coercion to `Dimension(1)`. Root cause is a too-strict equality check (`dim == Dimension(1)`) instead of the semantic `is_dimensionless(dim)` check.

Existing tests to reference (not to modify): `sympy/physics/units/tests/test_quantities.py` lines ~189, ~341-405, 520, 541, which exercise `_collect_factor_and_dimension` directly.

This is a reference for where the fix belongs, not a verified fix — see approach `function-branch-dimensionless-check` in research approaches for the (unverified) proposed change.

### X6 — This topic's pylint-aspect mismatches are an instance of a general pattern

R1 here is one instance of a cross-topic aspect-generation bug: see [[aspect-pylint-contamination#R1]] for the general rule and full list of affected aspect names/topics before re-investigating any of them.

### X7 — Confirmed pylint bug mechanism: os.walk root lacks trailing slash, breaks anchored ignore-paths regex

In pylint's installed package (site-packages, not a local git repo here), pylint/lint/pylinter.py:_discover_files (~lines 639-669) DOES call _is_ignored_file(root, ...) on every os.walk root — the check is not omitted. But os.walk yields directory roots with no trailing separator (e.g. 'src/gen', never 'src/gen/'). A common, natural ignore-paths regex like `^src/gen/.*$` matches subpaths ('src/gen/sub') but NOT the bare root string 'src/gen' itself, because there's no '/' + content after 'gen'. Net effect: files directly inside the ignored top-level directory leak through unignored, while deeper files/subpackages are correctly skipped once os.walk descends further. Verified both via direct re.match matrix and a real os.walk trace over a throwaway tree (tmp/research/regex_test.py in that investigation's scratch dir). See approaches trailing-separator-normalization, exact-or-prefix-match-instead-of-pure-regex, and rejected require-optional-suffix-in-user-regex for candidate fixes/non-fixes on topic sympy__sympy-24066.
