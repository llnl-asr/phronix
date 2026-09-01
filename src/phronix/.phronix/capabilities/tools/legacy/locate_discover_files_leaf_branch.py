import re

def register(mcp):
    @mcp.tool()
    def locate_discover_files_leaf_branch(pylinter_path: str) -> str:
        """Locate the else-branch in _discover_files that yields leaf .py files
        without filtering them through _is_ignored_file, given a path to
        pylint/lint/pylinter.py. Returns the matching line numbers and snippet."""
        with open(pylinter_path) as f:
            lines = f.readlines()
        start = None
        for i, line in enumerate(lines):
            if "_discover_files" in line and "def " in line:
                start = i
                break
        if start is None:
            return "NOT FOUND: _discover_files definition"
        snippet = []
        for i in range(start, min(start + 60, len(lines))):
            if "yield from" in lines[i] and "endswith" in lines[i]:
                snippet.append(f"{i+1}: {lines[i].rstrip()}")
        if not snippet:
            return "NOT FOUND: leaf-file yield branch (may already be patched)"
        return "\n".join(snippet)
