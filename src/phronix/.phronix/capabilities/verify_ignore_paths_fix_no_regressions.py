import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def verify_ignore_paths_fix_no_regressions(repo_root: str) -> str:
        """Run tests/lint/unittest_lint.py and tests/lint/unittest_expand_modules.py in
        *repo_root* (pytest -q) and report pass/fail. Use this after patching
        pylint/lint/pylinter.py::_discover_files to confirm every existing --ignore,
        --ignore-patterns and --ignore-paths / --recursive parametrization still passes.
        """
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/lint/unittest_lint.py",
                "tests/lint/unittest_expand_modules.py",
                "-q",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = proc.stdout[-4000:] + "\n" + proc.stderr[-2000:]
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return f"{status} (exit {proc.returncode})\n{output}"
