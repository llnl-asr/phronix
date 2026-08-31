"""Verify that ignore-paths works with --recursive=y in pylint.

Runs the test_ignore_path_recursive test to confirm the fix.
"""

import subprocess
import sys
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def verify_recursive_ignore_paths(repo_path: str) -> str:
        """Run test to verify ignore-paths works with recursive mode.
        
        Args:
            repo_path: Path to the pylint repository
            
        Returns:
            Test result indicating pass/fail
        """
        repo = Path(repo_path)
        
        if not repo.exists():
            return f"Error: Repository path {repo_path} does not exist"
        
        # Run the specific test
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_self.py::TestRunTC::test_ignore_path_recursive",
                "-xvs"
            ],
            cwd=repo,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return f"✓ Test passed: ignore-paths works correctly with --recursive=y\\n\\n{result.stdout}"
        else:
            return f"✗ Test failed (exit code {result.returncode}):\\n\\nSTDOUT:\\n{result.stdout}\\n\\nSTDERR:\\n{result.stderr}"
