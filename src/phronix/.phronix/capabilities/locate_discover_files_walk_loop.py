import re


def register(mcp):
    @mcp.tool()
    def locate_discover_files_walk_loop(repo_root: str) -> str:
        """Find the `for root, _, files in os.walk(something):` loop in
        PyLinter._discover_files inside pylint/lint/pylinter.py, and return
        the surrounding source lines with their line numbers.
        """
        path = f"{repo_root.rstrip('/')}/pylint/lint/pylinter.py"
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            return f"error reading {path}: {exc}"

        start = None
        for i, line in enumerate(lines):
            if re.search(r"for\s+root,\s*_,\s*files\s+in\s+os\.walk\(", line):
                start = i
                break

        if start is None:
            return f"os.walk loop not found in {path}"

        lo = max(0, start - 5)
        hi = min(len(lines), start + 25)
        numbered = [f"{n + 1}: {lines[n]}" for n in range(lo, hi)]
        return f"{path}\n" + "".join(numbered)
