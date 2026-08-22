"""Verify whether a pylint checkout's recursive file discovery respects ignore-paths."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap


def register(mcp):
    @mcp.tool()
    def verify_recursive_ignore_paths(repo_root: str, ignore_regex: str = r"^src/gen/.*$") -> str:
        """Build a temp tree with src/main.py (should survive) and src/gen/about.py
        (should be excluded by an ignore-paths regex like '^src/gen/.*$'), run the
        given repo's PyLinter._discover_files(['src']) against it in a subprocess
        that imports pylint from repo_root, and report which files were yielded.

        Returns a message stating PASS (ignored file excluded, other file kept) or
        FAIL (with the actual file list), so this can be used both to reproduce the
        bug before a fix and to confirm the fix afterward.
        """
        tmp = tempfile.mkdtemp(prefix="verify_ignore_paths_")
        try:
            os.makedirs(os.path.join(tmp, "src", "gen"))
            with open(os.path.join(tmp, "src", "main.py"), "w") as f:
                f.write("y = 1\n")
            with open(os.path.join(tmp, "src", "gen", "about.py"), "w") as f:
                f.write("x = 1\n")

            script = textwrap.dedent(
                f"""
                import re, sys
                sys.path.insert(0, {repo_root!r})
                from pylint.lint.pylinter import PyLinter
                lint = PyLinter()
                lint.config.recursive = True
                lint.config.ignore = ()
                lint.config.ignore_patterns = []
                lint.config.ignore_paths = [re.compile({ignore_regex!r})]
                print(sorted(lint._discover_files(['src'])))
                """
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return f"error running check: {result.stderr}"
            files = result.stdout.strip()
            excluded = "gen/about.py" not in files.replace(os.sep, "/")
            kept = "main.py" in files
            if excluded and kept:
                return f"PASS: ignored file excluded, other file kept -- {files}"
            return f"FAIL: unexpected discovery result -- {files}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
