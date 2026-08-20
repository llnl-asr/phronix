import os
import re
import tempfile
import shutil

def register(mcp):
    @mcp.tool()
    def repro_discover_files_ignore_paths(repo_root: str, ignore_paths_regex: str) -> str:
        """Create a small synthetic directory tree with a nested non-package
        .py file plus a sibling file, run PyLinter._discover_files against it
        with the given ignore_paths_regex (a python regex string matched
        against full file paths), and report which files were yielded.
        Requires repo_root's pylint package to be importable (run from repo
        root or with it on sys.path)."""
        import sys
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pylint.lint.pylinter import PyLinter

        tmpdir = tempfile.mkdtemp(prefix="discover_files_repro_")
        try:
            sub = os.path.join(tmpdir, "subdir")
            os.makedirs(sub)
            target = os.path.join(sub, "module.py")
            sibling = os.path.join(sub, "keep.py")
            with open(target, "w") as f:
                f.write("x = 1\n")
            with open(sibling, "w") as f:
                f.write("y = 2\n")

            linter = PyLinter()
            linter.config.ignore = ("CVS",)
            linter.config.ignore_patterns = ()
            linter.config.ignore_paths = [re.compile(ignore_paths_regex)]

            results = sorted(os.path.relpath(p, tmpdir) for p in linter._discover_files([tmpdir]))
            excluded = os.path.relpath(target, tmpdir) not in results
            return (
                f"yielded: {results}\n"
                f"target excluded: {excluded} (expected True after fix)"
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
