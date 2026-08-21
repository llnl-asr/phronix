---
name: sympy-sympy-24066
description: Notes on sympy__sympy-24066: mismatched pylint-flavored aspects to ignore, and the actual dimensionless/exp() bug in sympy.physics.units.
subject: sympy-sympy-24066
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Aspects describing pylint ignore-paths/discover_files internals are misassigned to this topic |
| `X1` | References | Actual bug: SI._collect_factor_and_dimension() doesn't recognize exp(dimensionless) as dimensionless |

## Instructions

## Rules

### R1 — Aspects describing pylint ignore-paths/discover_files internals are misassigned to this topic

Three aspect names assigned to sympy__sympy-24066 (base commit 514579c655bf) all describe pylint-dev/pylint internals, not sympy: `expand_modules_vs_discover_files_paths`, `regex_anchoring_relative_vs_absolute`, and `discover_files_ignore_check`. Each references pylint/lint/pylinter.py `check()`/`_discover_files()`, pylint/lint/expand_modules.py `expand_modules()`/`_is_in_ignore_list_re`, `_is_ignored_file`, `--recursive=y`, or ignore-paths regex config — none of which exist in this checkout (no pylint package, no .pylintrc, verified by grep).

**Why:** A sibling phronix task for pylint-dev/pylint-7080 runs on the same shared machine; aspect text leaked from that task into this one's assignment.

**How to apply:** If any of these three (or a similarly pylint-flavored aspect) is assigned again, do not grep/investigate — flag the mismatch and go straight to [[sympy-sympy-24066#X1]].

## References

### X1 — Actual bug: SI._collect_factor_and_dimension() doesn't recognize exp(dimensionless) as dimensionless

The real issue for sympy__sympy-24066 is in sympy/physics/units/unitsystem.py: `UnitSystem._collect_factor_and_dimension()` (also reachable via `SI.get_dimension_system()`) fails to recognize that an `exp(expr)` argument is dimensionless when `expr` itself is dimensionless (e.g. `units.second / (units.ohm * units.farad)`), raising a spurious `ValueError: Dimension of "exp(...)" is Dimension(...), but it should be Dimension(1)`.

Productive investigation directions: how `_collect_factor_and_dimension` handles `exp`/other `Function` arguments versus how it handles `Pow`, and why `is_dimensionless`/`Dimension.is_dimensionless()` isn't applied to function arguments before dimension propagation. See [[sympy-sympy-24066#R1]] for why the pylint-flavored aspects should be ignored.
