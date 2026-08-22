# Lessons — software-pylint-recursive-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Normalizing at one caller in multi-caller path is insufficient

**2026-08-18** — **Symptom**: Target test `test_ignore_path_recursive_current_dir` fails. File `ignored_subdirectory/failing.py` appears in pylint output when it should be filtered by ignore-paths pattern.

**What was tried**: Added `os.path.normpath(root)` at line 601 in `pylint/lint/pylinter.py`, normalizing the path passed to `_is_ignored_file()` call in `_discover_files()`.

**Root cause of failure**: The normalized path at line 601 only affects directory-level filtering. Individual file paths yielded at line 614 (`os.path.join(root, file)`) use the original unnormalized `root` variable. Those unnormalized file paths flow to `expand_modules()` which calls `_is_ignored_file()` again at line 78, and that second call receives unnormalized paths with `./` prefixes, so patterns fail to match.

**Why the location was wrong**: `_is_ignored_file()` has TWO call sites in the recursive path (one in `_discover_files`, one in `expand_modules`). Normalizing at only the first call site left the second broken.

**Correct fix**: Add `element = os.path.normpath(element)` at the START of `_is_ignored_file()` function body (expand_modules.py line 55). This fixes all call sites with one change, as proven by PR #7080.

### L2 — Normalization in _is_ignored_file fixes all call sites

**2026-08-18** — **2026-08-18** — **Symptom**: With `--recursive=y`, files matching `ignore-paths` patterns in pyproject.toml are still linted instead of being ignored.

**Root cause**: Paths passed to `_is_ignored_file()` contain relative path prefixes like `./` that prevent regex patterns from matching. The function has multiple call sites (recursive in `_discover_files`, non-recursive in `expand_modules`), making caller-side normalization insufficient.

**Fix that works**: Add `element = os.path.normpath(element)` as the first line inside `_is_ignored_file()` function body (expand_modules.py, immediately after the function signature). This defensive normalization ensures all paths are normalized before regex matching, regardless of which call site invoked the function.

**Verification**: Test `test_ignore_path_recursive` passes after this change. Files in directories matching `ignore-paths` patterns are properly filtered out during recursive linting.

### L3 — Fix confirmed end-to-end: attempt with only the normpath change passed

**2026-08-22** — **2026-08-22** — A full attempt applying exactly `L2`'s fix (only `element = os.path.normpath(element)` added at the top of `_is_ignored_file()` in `pylint/lint/expand_modules.py`, one line, no other changes) was run and judged **Resolved: YES** — target test `test_ignore_path_recursive_current_dir` 1/1 passing, regression suite 119/120 passing.

The one regression failure, `TestCallbackOptions.test_generate_toml_config_disable_symbolic_names`, is unrelated: it fails with `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key` inside `_generate_config_file` (a `--generate-toml-config`/tomlkit-version incompatibility), and it did not block the task from passing. Do not spend time trying to fix or explain that failure as a consequence of the ignore-paths normpath change — it is pre-existing and orthogonal.

This closes the loop on `L1`/`L2`: the one-line fix is not just theoretically correct, it is proven sufficient with no accompanying changes needed elsewhere.
