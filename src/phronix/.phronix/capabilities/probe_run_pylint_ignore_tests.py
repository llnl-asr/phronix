import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def probe_run_pylint_ignore_tests(repo_path: str) -> str:
        """Run pylint's ignore-paths/recursive related tests.

        Executes pytest against tests/lint/unittest_lint.py and
        tests/test_self.py -k "ignore or recursive" inside *repo_path*.

        Returns a JSON string: {status, returncode, stdout, stderr}.
        """
        import json

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/lint/unittest_lint.py",
                "tests/test_self.py",
                "-k",
                "ignore or recursive",
                "-q",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return json.dumps(
            {
                "status": "ok",
                "returncode": proc.returncode,
                "stdout": proc.stdout[-8000:],
                "stderr": proc.stderr[-4000:],
            }
        )
