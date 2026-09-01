import re
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def find_discover_files_gap(repo_path: str) -> str:
        """Inspect pylint/lint/pylinter.py's _discover_files for the else-branch
        that yields loose .py files without calling _is_ignored_file per file.

        Returns a report noting the line range of _discover_files, whether the
        root-level _is_ignored_file check exists, and whether the else-branch
        (files without __init__.py) filters individual file paths.
        """
        target = Path(repo_path) / "pylint" / "lint" / "pylinter.py"
        if not target.exists():
            return f"NOT FOUND: {target}"
        text = target.read_text()
        m = re.search(r"def _discover_files\(.*?\n(?:.*\n)*?(?=\n    def )", text)
        if not m:
            return "_discover_files method not found"
        body = m.group(0)
        has_root_check = "_is_ignored_file(\n" in body and "root," in body
        else_branch = re.search(r"else:\s*\n(.*\n)*?\s*\)\s*\n", body)
        else_text = else_branch.group(0) if else_branch else ""
        per_file_check = "_is_ignored_file" in else_text
        report = [
            "_discover_files found.",
            f"root-level _is_ignored_file check present: {has_root_check}",
            f"else-branch per-file _is_ignored_file check present: {per_file_check}",
        ]
        if not per_file_check:
            report.append(
                "GAP CONFIRMED: loose .py files yielded in the else-branch are "
                "never individually checked against ignore/ignore-patterns/ignore-paths."
            )
        return "\n".join(report)
