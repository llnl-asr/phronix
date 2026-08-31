import os
import tempfile
import shutil

def register(mcp):
    @mcp.tool()
    def probe_pylint_ignore_paths_recursive(repo_root: str, ignore_pattern: str = r"^.*/src/gen/.*$") -> str:
        """Reproduce/verify the pylint bug where --recursive=y file discovery does not honor ignore-paths for files inside nested ignored subdirectories.

        Builds a temp package tree: pkg/main.py, pkg/src/gen/generated.py, pkg/src/gen/sub/deep.py.
        Runs PyLinter._discover_files() with config.recursive=True and config.ignore_paths=[ignore_pattern],
        then reports which files were yielded. The bug is present if any file under src/gen/ is yielded.

        Args:
            repo_root: path to the pylint checkout (must be importable, e.g. via sys.path or already installed).
            ignore_pattern: regex for ignore-paths; default matches the issue's reported pattern shape.
        """
        import sys
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pylint.lint import PyLinter

        tmpdir = tempfile.mkdtemp(prefix="pylint_ignore_probe_")
        try:
            pkg = os.path.join(tmpdir, "pkg")
            gen = os.path.join(pkg, "src", "gen", "sub")
            os.makedirs(gen)
            with open(os.path.join(pkg, "main.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(pkg, "src", "gen", "generated.py"), "w") as f:
                f.write("y = 2\n")
            with open(os.path.join(gen, "deep.py"), "w") as f:
                f.write("z = 3\n")

            linter = PyLinter()
            linter.config.recursive = True
            linter.config.ignore = ()
            linter.config.ignore_patterns = ()
            linter.config.ignore_paths = [__import__("re").compile(ignore_pattern)]

            found = sorted(
                os.path.relpath(p, tmpdir) for p in linter._discover_files([pkg])
            )
            leaked = [p for p in found if "src/gen" in p.replace(os.sep, "/")]
            return (
                f"discovered={found}\n"
                f"leaked_ignored_files={leaked}\n"
                f"bug_present={bool(leaked)}"
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    return None
