"""Apply the discover_files_check_ignore_paths_per_file fix to a pylint checkout."""
import os


OLD = '''                    else:
                        yield from (
                            os.path.join(root, file)
                            for file in files
                            if file.endswith(".py")
                        )'''

NEW = '''                    else:
                        yield from (
                            os.path.join(root, file)
                            for file in files
                            if file.endswith(".py")
                            and not _is_ignored_file(
                                os.path.join(root, file),
                                self.config.ignore,
                                self.config.ignore_patterns,
                                self.config.ignore_paths,
                            )
                        )'''


def register(mcp):
    @mcp.tool()
    def apply_ignore_paths_recursive_fix(repo_root: str) -> str:
        """Patch <repo_root>/pylint/lint/pylinter.py to filter individually-yielded
        files in _discover_files through _is_ignored_file, so --recursive=y
        respects ignore-paths/ignore-patterns/ignore for files inside directories
        that don't themselves match an anchored ignore-paths regex.

        Idempotent: if the fix is already applied, reports that and makes no change.
        Returns a status message describing what happened.
        """
        path = os.path.join(repo_root, "pylint", "lint", "pylinter.py")
        if not os.path.isfile(path):
            return f"error: no such file {path}"
        text = open(path, encoding="utf-8").read()
        if NEW in text:
            return "already patched: no change made"
        if OLD not in text:
            return (
                "error: expected unpatched pattern not found in "
                f"{path} -- file may have diverged from the known baseline"
            )
        text = text.replace(OLD, NEW)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return f"patched {path}"
