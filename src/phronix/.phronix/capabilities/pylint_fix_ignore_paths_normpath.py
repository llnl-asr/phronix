from __future__ import annotations

import subprocess
from pathlib import Path


OLD = '''def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    basename = os.path.basename(element)'''

NEW = '''def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    element = os.path.normpath(element)
    basename = os.path.basename(element)'''


def register(mcp):
    @mcp.tool()
    def pylint_apply_ignore_paths_normpath_fix(repo_root: str) -> str:
        """Apply the one-line fix to pylint/lint/expand_modules.py.

        Inserts `element = os.path.normpath(element)` at the top of
        `_is_ignored_file()` so that ignore/ignore-patterns/ignore-paths
        matching works when pylint is run with --recursive=y against a
        cwd-relative target such as ".", where os.walk() yields roots
        prefixed with "./" that anchored regexes (e.g. "^subdir/.*$")
        would otherwise never match.

        Idempotent: if the fix is already present, reports that and makes
        no change. Returns a JSON string: {"status": "applied"|"already_present"|"pattern_not_found", "path": str}.
        """
        target = Path(repo_root) / "pylint" / "lint" / "expand_modules.py"
        text = target.read_text()
        if "element = os.path.normpath(element)" in text:
            return f'{{"status": "already_present", "path": "{target}"}}'
        if OLD not in text:
            return f'{{"status": "pattern_not_found", "path": "{target}"}}'
        target.write_text(text.replace(OLD, NEW))
        return f'{{"status": "applied", "path": "{target}"}}'

    @mcp.tool()
    def pylint_verify_ignore_paths_recursive_current_dir(repo_root: str) -> str:
        """Reproduce the issue and confirm the fix: run pylint --recursive=y
        from inside tests/regrtest_data/directory using "." as the target,
        with an anchored ignore pattern for each of the three ignore
        mechanisms (--ignore, --ignore-patterns, --ignore-paths), and
        report each exit code. Exit code 0 means the ignored subdirectory
        (which contains a file that would otherwise fail linting) was
        correctly skipped; nonzero means it was not.

        Returns a JSON string: {"ignore": int, "ignore_patterns": int, "ignore_paths": int}.
        """
        cwd = Path(repo_root) / "tests" / "regrtest_data" / "directory"
        env_pythonpath = str(Path(repo_root).resolve())
        cases = {
            "ignore": ["--ignore=ignored_subdirectory"],
            "ignore_patterns": ["--ignore-patterns=^ignored_.*$"],
            "ignore_paths": ["--ignore-paths=^ignored_subdirectory/.*$"],
        }
        results = {}
        for key, extra_args in cases.items():
            proc = subprocess.run(
                ["python", "-m", "pylint", "--recursive=y", ".", *extra_args],
                cwd=str(cwd),
                env={"PYTHONPATH": env_pythonpath, "PATH": "/usr/bin:/bin"},
                capture_output=True,
                text=True,
            )
            results[key] = proc.returncode
        import json as _json

        return _json.dumps(results)
