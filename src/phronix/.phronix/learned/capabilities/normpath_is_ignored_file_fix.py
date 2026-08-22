import os


def register(mcp):
    @mcp.tool()
    def apply_normpath_is_ignored_file_fix(repo_root: str) -> str:
        """Insert `element = os.path.normpath(element)` at the top of
        _is_ignored_file in <repo_root>/pylint/lint/expand_modules.py, right
        before the `basename = os.path.basename(element)` line. Idempotent:
        if the normpath line is already present, does nothing. Returns a
        status string describing what happened.
        """
        path = os.path.join(repo_root, "pylint", "lint", "expand_modules.py")
        with open(path, encoding="utf-8") as f:
            text = f.read()

        marker = "    basename = os.path.basename(element)"
        fix_line = "    element = os.path.normpath(element)\n"

        if fix_line.strip() in text:
            return "already applied: normpath line present"

        if marker not in text:
            return "error: could not locate insertion marker"

        text = text.replace(marker, fix_line + marker, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return "applied: inserted normpath(element) into _is_ignored_file"
