# Lessons — pylint-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --recursive=y ignored ignore-paths regexes (pylint-dev/pylint#7080)

**2026-08-20** — Symptom: with `--recursive=y`, files matching `ignore-paths` regexes (e.g. `^src/gen/.*$`) were still linted, even though the same config works without `--recursive`.

Root cause: `_is_ignored_file` in pylint/lint/expand_modules.py only tested the raw `element` path (as produced by directory walking, which can be OS-separator-inflected, relative in an unexpected form, or otherwise not matching the string shape the user's regex assumes) against `ignore_list_paths_re`. It never normalized separators or tried absolute/relative/normalized variants, so a regex anchored like `^src/gen/.*$` failed to match paths built with `os.sep` on Windows or with different relative bases during recursive walk.

Fix that was verified to pass the target test: in `_is_ignored_file`, also check `_is_in_ignore_list_re` against: `os.path.normpath(element).replace(os.sep, "/")`, `os.path.abspath(element).replace(os.sep, "/")`, and `os.path.relpath(element).replace(os.sep, "/")`, in addition to the existing raw-`element` check. This was a minimal, additive OR-chain — no removal of existing checks.

Unrelated: in this environment, `tests/test_self.py::TestCallbackOptions::test_generate_toml_config` and `test_generate_toml_config_disable_symbolic_names` fail regardless of this change, due to a `tomlkit.exceptions.TOMLKitError: Can't add a table to a dotted key` — this is a pre-existing tomlkit-version incompatibility in `_generate_config_file`, not caused by ignore-paths changes. Don't waste time attributing that failure to an ignore-paths fix.
