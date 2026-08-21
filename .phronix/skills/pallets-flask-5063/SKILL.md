---
name: pallets-flask-5063
description: Notes on pallets__flask-5063: mismatched pylint-flavored aspects to ignore, and where to actually work (flask routes CLI / TestRoutes).
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R2` | Rules | Aspect prompt for existing_test_coverage_gap was mismatched to this topic |
| `R3` | Rules | flask routes output format constraint for TestRoutes regression tests |
| `R4` | Rules | Aspects referencing pylint ignore-paths/expand_modules internals are misassigned to this topic |
| `R5` | Rules | Sandbox's default Python 3.13 venv can't run tests/test_cli.py |

## Instructions

## Rules

### R2 — Aspect prompt for existing_test_coverage_gap was mismatched to this topic

The existing_test_coverage_gap aspect prompt for topic pallets__flask-5063 references tests/lint/test_expand_modules.py and tests/test_self.py with ignore-paths/--recursive semantics — these are pylint testing artifacts and do not exist anywhere in this repo. This task is actually pallets/flask issue requesting a Domain/subdomain column in `flask routes` CLI output. Do not spend budget searching for those pylint files again in this topic; go straight to tests/test_cli.py::TestRoutes and src/flask/cli.py::routes_command instead. See [[flask-routes-subdomain#X1]] for the issue itself, [[flask-repo-orientation#X1]] for where the code lives, and [[pallets-flask-5063#R4]] for a second, differently-named aspect leak on this same topic.

### R3 — flask routes output format constraint for TestRoutes regression tests

tests/test_cli.py::TestRoutes (test_simple, test_sort) uses an expect_order helper that checks line[:len(expect)] against the endpoint name, treating Endpoint as the first field of each output row (after 2 header lines). Any new column (e.g. a Domain column for the subdomain feature requested in the issue) must not be inserted before Endpoint as a new leading column, or it will break test_sort/test_simple by shifting the string prefix. Append new columns at the end, or make them conditional, to stay compatible. src/flask/cli.py::routes_command is the implementation to modify; it builds the table via click.HelpFormatter and app.url_map.iter_rules(), where each werkzeug Rule has .subdomain, combinable with app.config['SERVER_NAME'] for the full domain.

### R4 — Aspects referencing pylint ignore-paths/expand_modules internals are misassigned to this topic

Aspect names `expand_modules_vs_discover_files_paths` and `regex_anchoring_relative_vs_absolute`, when assigned to pallets__flask-5063 (base commit 182ce3dd15df), both describe pylint-dev/pylint internals — pylint/lint/pylinter.py `check()`, pylint/lint/expand_modules.py `expand_modules()`/`_is_in_ignore_list_re`, `_discover_files()`, `_iterate_file_descrs`, `_is_ignored_file`, `--recursive=y`, ignore-paths regex — none of which exist anywhere in this Flask checkout (verified via repo-wide find/grep).

**Why:** aspect text leaks in from a sibling pylint-dev/pylint-7080 task sharing the same machine — the same class of leak recurs on other topics too, see [[sympy-sympy-24066#R1]] and [[pylint-dev-pylint-7080#R4]].

**How to apply:** do not re-grep for these files; flag the mismatch immediately and redirect to the real issue at [[pallets-flask-5063#R2]]. If a Flask-analogue is ever wanted, it needs a freshly-scoped aspect against real Flask code, not a reinterpretation of the pylint aspect.

### R5 — Sandbox's default Python 3.13 venv can't run tests/test_cli.py

Two unrelated environment failures block `tests/test_cli.py` under the sandbox's default Python 3.13 venv: an `ast.Str` `DeprecationWarning` from anaconda's system Python loading `conftest.py` (fatal since `pyproject.toml` sets `filterwarnings=error`), and separately a `pytest`/`monkeypatch.notset` incompatibility with 3.13.

**Why:** reported repeatedly across tune-stage cycles — both are tooling noise, not regressions in a candidate fix.

**How to apply:** if `tests/test_cli.py` fails to collect, check interpreter/warning source before blaming the patch — use the repo's intended interpreter, not the sandbox default.
