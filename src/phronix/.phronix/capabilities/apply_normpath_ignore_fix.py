import os


def register(mcp):
    @mcp.tool()
    def apply_normpath_ignore_fix(repo_root: str) -> str:
        """Ensure pylint/lint/expand_modules.py::_is_ignored_file normalizes
        its `element` argument with os.path.normpath() before matching it
        against ignore/ignore-patterns/ignore-paths. Idempotent: does
        nothing if the normalization is already present. Returns a status
        string describing what happened.
        """
        path = os.path.join(repo_root, "pylint", "lint", "expand_modules.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if "element = os.path.normpath(element)" in content:
            return "already applied: normpath present in _is_ignored_file"

        marker = "    basename = os.path.basename(element)"
        if marker not in content:
            return "error: could not find insertion point (basename = os.path.basename(element))"

        content = content.replace(
            marker,
            "    element = os.path.normpath(element)\n" + marker,
            1,
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "applied: inserted element = os.path.normpath(element) into _is_ignored_file"
