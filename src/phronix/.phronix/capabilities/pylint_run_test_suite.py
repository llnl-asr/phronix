"""Run pylint's test suite to detect regressions.

Executes the repository's pytest-based test suite, focusing on tests related
to recursive mode and ignore functionality.
"""

import subprocess
from pathlib import Path

def register(mcp):
    @mcp.tool()
    def pylint_run_test_suite(repo_root: str, focus_tests: str = "") -> str:
        """Run pylint's test suite or a subset of tests.
        
        Args:
            repo_root: Path to the pylint repository root
            focus_tests: Optional test path/pattern to run specific tests (e.g., "tests/test_self.py::test_recursive")
            
        Returns:
            Test results with pass/fail counts and any failures
        """
        repo_path = Path(repo_root)
        
        if not (repo_path / "tests").exists():
            return f"ERROR: tests directory not found in {repo_root}"
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", "-v"]
        
        if focus_tests:
            cmd.append(focus_tests)
        else:
            # Run ignore/recursive related tests
            cmd.extend([
                "tests/test_self.py",
                "-k", "ignore or recursive"
            ])
        
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout + result.stderr
        
        # Parse results
        if result.returncode == 0:
            return f"PASS: All tests passed\n\n{output[-1000:]}"  # Last 1000 chars
        else:
            # Extract failure summary
            lines = output.split("\n")
            summary_start = -1
            for i, line in enumerate(lines):
                if "FAILED" in line or "ERROR" in line:
                    summary_start = max(0, i - 5)
                    break
            
            if summary_start >= 0:
                summary = "\n".join(lines[summary_start:])
            else:
                summary = output[-2000:]  # Last 2000 chars if no clear failure
            
            return f"FAIL: Tests failed with return code {result.returncode}\n\n{summary}"
