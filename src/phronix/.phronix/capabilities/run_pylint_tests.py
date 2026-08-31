"""Run pylint test suite."""

import subprocess
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def run_pylint_tests(repo_path: str, test_pattern: str = "test_self.py") -> dict:
        """Run pylint tests and return results.
        
        Args:
            repo_path: Path to the pylint repository root
            test_pattern: Test file pattern to run (default: test_self.py)
            
        Returns:
            Dictionary with test results including exit_code, stdout, and stderr
        """
        repo = Path(repo_path)
        
        if not repo.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_path}",
                "exit_code": -1
            }
        
        # Run pytest on the specified test pattern
        test_path = repo / "tests" / test_pattern
        
        result = subprocess.run(
            ["python", "-m", "pytest", str(test_path), "-v"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "test_file": str(test_path)
        }
