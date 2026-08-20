# Lessons — pylint-dev-pylint-7080

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Basic pyproject.toml + ignore-paths + --recursive=y case already works at base commit; bug repro not found

**2026-08-19** — At base commit 3c5eca2ded3d, _discover_files (lines 585-619) already contains the _is_ignored_file check (using self.config.ignore, ignore_patterns, ignore_paths) that skips ignored subtrees during recursive discovery — this logic is NOT missing. Reproduced locally: a repo with pyproject.toml `ignore-paths = ["^src/gen/.*$", ...]`, running `Run(['--recursive=y', 'src/'])`, correctly skipped src/gen/about.py and linted only src/main.py. Control (no pyproject.toml) linted both files, confirming ignore-paths was the suppressing mechanism. So the literal simple case from the GH issue's config snippet does NOT reproduce the bug on this checkout. Untested remaining leads for wherever the real defect is: (1) directories that themselves have __init__.py (package case) vs plain directories, (2) Windows path separator (\\ vs /) handling — issue reporter used Windows paths, untestable on this Linux env, (3) precedence/order between _is_ignored_file's checks and os.walk/skip_subtrees pruning in more complex nested-ignore cases, (4) possibility that base commit 3c5eca2ded3d (on the 2.15 line) already contains a partial fix for the original 2.14.1-reported bug, making the remaining gap narrower than the full issue. This aspect (correct_fix_shape) did not find the repro — that belongs to whichever aspect covers the defect mechanism; this note just says the config-line-604 swap area is not where to look.
