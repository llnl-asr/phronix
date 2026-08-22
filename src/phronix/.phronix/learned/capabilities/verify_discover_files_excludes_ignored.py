import os
import re
import sys
import tempfile


def register(mcp):
    @mcp.tool()
    def verify_discover_files_excludes_ignored(repo_root: str) -> str:
        """Create a scratch directory tree with a nested non-package file
        that should be excluded by an ignore-paths regex, plus a sibling
        file that should be kept, then call PyLinter()._discover_files()
        directly and assert the excluded/kept sets match expectations.
        Returns 'ok: ...' on success or 'FAIL: ...' with details.
        """
        sys.path.insert(0, repo_root)
        from pylint.lint.pylinter import PyLinter

        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "ignored_subdirectory")
            os.makedirs(sub)
            bad = os.path.join(sub, "failing.py")
            good = os.path.join(tmp, "keep.py")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("import re\n")
            with open(good, "w", encoding="utf-8") as f:
                f.write("'''doc'''\n")

            linter = PyLinter()
            linter.config.ignore = []
            linter.config.ignore_patterns = []
            linter.config.ignore_paths = [re.compile(r".*ignored_subdirectory.*")]

            found = set(linter._discover_files([tmp]))

        if bad in found:
            return f"FAIL: ignored file was not excluded: {bad} in {found}"
        if good not in found:
            return f"FAIL: sibling file was incorrectly excluded: {good} not in {found}"
        return "ok: ignored file excluded, sibling file kept"
