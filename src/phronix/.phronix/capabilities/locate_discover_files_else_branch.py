import re


def register(mcp):
    @mcp.tool()
    def locate_discover_files_else_branch(repo_root: str) -> str:
        """Locate the else-branch in PyLinter._discover_files (pylint/lint/pylinter.py)
        that yields individual files during os.walk without applying _is_ignored_file,
        which is the root cause of --recursive=y ignoring ignore-paths/ignore-patterns/ignore.
        Returns the file path and matching line numbers.
        """
        path = f"{repo_root}/pylint/lint/pylinter.py"
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        start = None
        for i, line in enumerate(lines):
            if "_discover_files" in line and "def " in line:
                start = i
                break
        if start is None:
            return "_discover_files not found in " + path

        end = min(start + 60, len(lines))
        snippet = lines[start:end]

        hits = []
        for i, line in enumerate(snippet, start=start + 1):
            if "yield os.path.join(root, file)" in line or re.search(r"^\s*else:\s*$", line):
                hits.append((i, line.rstrip("\n")))

        report = [f"file: {path}", f"_discover_files starts at line {start + 1}"]
        for lineno, text in hits:
            report.append(f"  L{lineno}: {text}")
        report.append(
            "Fix target: the yield inside the else-branch is missing a "
            "`and not _is_ignored_file(os.path.join(root, file), self.config.ignore, "
            "self.config.ignore_patterns, self.config.ignore_paths)` guard."
        )
        return "\n".join(report)
