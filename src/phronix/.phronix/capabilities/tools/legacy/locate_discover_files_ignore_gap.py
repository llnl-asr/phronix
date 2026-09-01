import re


def register(mcp):
    @mcp.tool()
    def locate_discover_files_ignore_gap(repo_root: str) -> str:
        """Read pylint/lint/pylinter.py's _discover_files method and report
        whether it calls _is_ignored_file on each individual discovered file
        (not just on directory roots). Returns a JSON-ish summary string
        with the method source snippet and a verdict.
        """
        import os

        path = os.path.join(repo_root, "pylint", "lint", "pylinter.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()

        m = re.search(r"def _discover_files\(.*?\n(?:.*\n)*?(?=\n    def |\Z)", src)
        if not m:
            return "NOT_FOUND: _discover_files method not found in %s" % path

        snippet = m.group(0)
        # Look for a per-file ignore check near the per-file yield.
        yield_lines = [l for l in snippet.splitlines() if "yield" in l and "file" in l]
        has_per_file_check = "_is_ignored_file" in snippet and any(
            "_is_ignored_file" in l for l in snippet.splitlines()
        )
        # More precise: does the per-file yield line itself (or its immediate
        # filter) reference _is_ignored_file?
        lines = snippet.splitlines()
        gap = True
        for i, l in enumerate(lines):
            if "yield" in l and "os.path.join(root, file)" in l:
                window = "\n".join(lines[max(0, i - 3): i + 1])
                if "_is_ignored_file" in window:
                    gap = False
                break

        verdict = "GAP_CONFIRMED" if gap else "GAP_NOT_PRESENT"
        return "%s\n---\n%s" % (verdict, snippet)
