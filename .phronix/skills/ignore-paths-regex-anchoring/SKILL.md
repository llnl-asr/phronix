---
name: ignore-paths-regex-anchoring
description: The ignore-paths-regex-anchoring subject.
subject: ignore-paths-regex-anchoring
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Generic finding: os.walk root strings break ^prefix/.*$-style ignore regexes (not applicable to sympy-21847) |


## Instructions

## Rules

## References

### X1 — Generic finding: os.walk root strings break ^prefix/.*$-style ignore regexes (not applicable to sympy-21847)

Standalone, repo-independent finding (verified via re.match, not tied to any specific codebase): patterns like `^src/gen/.*$` intended to mean "ignore this directory and everything below" do NOT match the bare directory-root string `os.walk` yields for that exact directory (no trailing slash) — only deeper paths like `src/gen/sub` or a manually-added `src/gen/` match. Additional silent-failure modes: backslash-separator patterns never match POSIX forward-slash paths; exact-match patterns (`^src/gen$`) only match the root itself, not descendants; unanchored substring patterns avoid the trailing-slash issue but false-positive on siblings like `src/gen-old`; a leading `./` prefix from `os.walk('.')` defeats patterns written without it.

This is real and reproducible pylint-style ignore-list-via-regex behavior (pylint 4.0.7, already installed in the shared venv, avoids it by matching `ignore_list_paths_re` against `os.path.normpath(element)`, the full path, rather than a bare walked root). It is NOT applicable to sympy__sympy-21847 — see [[sympy-sympy-21847#R5]]. File this only for a future topic that is actually about pylint's expand_modules ignore-paths handling.
