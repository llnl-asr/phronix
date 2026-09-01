import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def run_pylint_discovery_regression_tests(repo_path: str) -> str:
        """Run pytest against pylint's own tests relevant to file discovery,
        expand_modules, and ignore-paths handling, to confirm no regression
        after changing PyLinter._discover_files.

        Targets tests/test_self.py -k ignore and tests/lint/ if present.
        """
        results = []
        cmds = [
            [sys.executable, "-m", "pytest", "tests/test_self.py", "-k", "ignore", "-q"],
            [sys.executable, "-m", "pytest", "tests/lint", "-q"],
        ]
        for cmd in cmds:
            proc = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, timeout=300
            )
            results.append(
                f"$ {' '.join(cmd)}\nexit_code={proc.returncode}\n"
                f"{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}"
            )
        return "\n\n".join(results)
