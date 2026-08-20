import os
import re
import tempfile
import shutil

def register(mcp):
    @mcp.tool()
    def discover_files_ignore_scenarios(repo_root: str) -> str:
        """Exercise PyLinter._discover_files across several synthetic
        directory-tree scenarios: nested two-level file match via
        ignore-paths, a non-matching control regex, and the --ignore
        bare-filename mechanism. Reports pass/fail per scenario."""
        import sys
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pylint.lint.pylinter import PyLinter

        results = []

        def make_tree(base, files):
            for rel in files:
                path = os.path.join(base, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write("x = 1\n")

        def run_case(name, files, ignore=("CVS",), ignore_patterns=(), ignore_paths_res=(), expect_present=(), expect_absent=()):
            tmpdir = tempfile.mkdtemp(prefix="discover_scn_")
            try:
                make_tree(tmpdir, files)
                linter = PyLinter()
                linter.config.ignore = ignore
                linter.config.ignore_patterns = [re.compile(p) for p in ignore_patterns]
                linter.config.ignore_paths = [re.compile(p) for p in ignore_paths_res]
                got = set(os.path.relpath(p, tmpdir) for p in linter._discover_files([tmpdir]))
                ok = all(p in got for p in expect_present) and all(p not in got for p in expect_absent)
                results.append(f"{name}: {'PASS' if ok else 'FAIL'} (got={sorted(got)})")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

        run_case(
            "nested_two_level_ignore_paths_match",
            ["a/b/target.py", "a/b/keep.py"],
            ignore_paths_res=[r".*a/b/target\.py$"],
            expect_present=["a/b/keep.py"],
            expect_absent=["a/b/target.py"],
        )
        run_case(
            "control_non_matching_ignore_paths",
            ["a/target.py"],
            ignore_paths_res=[r".*nomatch.*"],
            expect_present=["a/target.py"],
        )
        run_case(
            "ignore_bare_filename",
            ["a/skip_me.py", "a/keep.py"],
            ignore=("CVS", "skip_me.py"),
            expect_present=["a/keep.py"],
        )

        return "\n".join(results)
