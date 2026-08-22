"""Run the pylint test files that cover ignore/ignore-patterns/ignore-paths handling."""
import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def run_ignore_paths_regression_tests(repo_root: str) -> str:
        """Run `pytest tests/lint/unittest_expand_modules.py tests/test_self.py -k ignore`
        in repo_root and return combined stdout/stderr plus the return code, so a
        fix to recursive ignore-paths handling can be checked for regressions
        against the project's own existing test coverage.
        """
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/lint/unittest_expand_modules.py",
                "tests/test_self.py",
                "-k",
                "ignore",
                "-q",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-40:])
        return f"returncode={result.returncode}\n{tail}"
