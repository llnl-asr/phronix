"""Locate the _discover_files discovery loop in pylint's PyLinter and report
which lines call the ignore-check helper, to see whether it's applied only
to directory roots or also to individual discovered files.
"""
import re


def register(mcp):
    @mcp.tool()
    def probe_locate_discover_files_loop(repo_root: str) -> str:
        """Find pylint/lint/pylinter.py's _discover_files method and report
        the line ranges of the method and every call to _is_ignored_file
        within it, so callers can see whether the ignore check runs per
        directory root only or also per individual file.

        Args:
            repo_root: path to a pylint checkout containing pylint/lint/pylinter.py
        """
        path = f"{repo_root.rstrip('/')}/pylint/lint/pylinter.py"
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as exc:
            return f"error: could not read {path}: {exc}"

        start = None
        end = None
        for i, line in enumerate(lines):
            if start is None and re.match(r"\s*def _discover_files\(", line):
                start = i
                continue
            if start is not None and re.match(r"\s{4}def \w", line):
                end = i
                break
        if start is None:
            return f"error: _discover_files not found in {path}"
        if end is None:
            end = len(lines)

        ignore_calls = [
            i + 1
            for i in range(start, end)
            if "_is_ignored_file" in lines[i] or "ignore" in lines[i].lower()
        ]

        return (
            f"_discover_files spans lines {start + 1}-{end} in {path}\n"
            f"lines mentioning ignore-checks: {ignore_calls}\n"
            "---\n" + "".join(lines[start:end])
        )
