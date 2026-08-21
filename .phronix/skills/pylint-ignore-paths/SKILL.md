---
name: pylint-ignore-paths
description: The pylint-ignore-paths subject.
subject: pylint-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to reproduce ignore-paths mismatches without running the CLI |
| `R1` | Rules | Windows/POSIX separator normalization is already solved — don't re-fix it |
| `R2` | Rules | Three call sites match ignore-paths against different path forms |

## Instructions

### I1 — How to reproduce ignore-paths mismatches without running the CLI

In this sandboxed env, `python3 -m pylint` end-to-end runs conflict with a globally-installed pylint on sys.path, blocking a true CLI repro. Instead call `pylint.lint.expand_modules.expand_modules(...)` and `pylint.lint.pylinter.PyLinter._discover_files(...)` directly (with sys.path injection to prefer the repo checkout) — this exercises the real internal logic faithfully. Build a throwaway fixture dir (e.g. under tmp/research/proj/src/{gen,other}/__init__.py) to test relative-arg vs absolute-arg and recursive vs non-recursive behavior. Not yet done: running the repo's existing test suite for ignore-paths (tests/lint/unittest_expand_modules.py or similar) to see what path forms existing tests already assume, before picking a fix — check this before implementing, since it constrains which fix approach (trailing-separator match vs full path-form normalization) is safe to land.

## Rules

### R1 — Windows/POSIX separator normalization is already solved — don't re-fix it

pylint/config/argument.py::_regexp_paths_csv_transfomer (added in 2.12, see doc/whatsnew/2/2.12/full.rst) already compiles every ignore-paths pattern as `<windows-form>|<posix-form>`, so a single user pattern already matches both separator styles. Confirmed present at HEAD of the pylint-7080 checkout. This is NOT the mechanism behind the --recursive=y ignore-paths bug (issue 7080), nor is it relevant to any other topic (repeatedly mis-assigned to pallets__flask-5063 and sympy__sympy-24066, both topic mismatches — see [[pallets-flask-5063#R4]] and [[sympy-sympy-24066#R1]]). Don't waste time re-investigating separator handling under any topic; the real mechanisms are the two path-form mismatches in R2/R3. Also tracked as a tried-and-refuted approach at [[discover-files#X25]].

### R2 — Three call sites match ignore-paths against different path forms

ignore-paths regexes are matched via re.Pattern.match (prefix-anchored, not fullmatch) at three call sites, each passing a DIFFERENT path-string form: (1) expand_modules.py::_is_ignored_file with `element` = CLI arg as typed (relative or absolute); (2) same function with `subfilepath` from astroid's get_module_files (os.walk results inherit the form of the dir passed in — relative in → relative out, absolute in → absolute out); (3) pylinter.py::_discover_files (only --recursive=y) calls _is_ignored_file with `root`, a bare directory path with NO trailing separator and NO filename (e.g. "src/gen"). A single user pattern can match only one form. The directory-root case (3) is detailed further at [[pylint-discover-files-ignore-paths#R1]]; the absolute-vs-relative case (1) is detailed at [[pylint-dev-pylint-7080#I2]].
