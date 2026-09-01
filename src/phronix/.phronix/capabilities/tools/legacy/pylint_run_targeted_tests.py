"""Capability to run specific pylint tests related to recursive mode and ignore-paths."""

import subprocess
import os


def register(mcp):
    @mcp.tool()
    def run_ignore_paths_tests(repo_path: str, test_pattern: str = "*recursive*,*ignore*,*expand_modules*") -> dict:
        """Run pylint tests related to recursive mode and ignore-paths.
        
        Args:
            repo_path: Path to the pylint repository root
            test_pattern: Comma-separated glob patterns for test files to run
            
        Returns:
            Dictionary with test results including status, output, and pass/fail counts
        """
        os.chdir(repo_path)
        
        # Run pytest with verbose output
        cmd = ["python", "-m", "pytest", "-xvs", "tests/lint/unittest_expand_modules.py", "tests/test_self.py", "-k", "ignore"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "summary": _extract_test_summary(result.stdout)
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Tests timed out after 300 seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _extract_test_summary(output: str) -> str:
        """Extract the test summary line from pytest output."""
        lines = output.split("\\n")
        for line in reversed(lines):
            if "passed" in line or "failed" in line or "error" in line:
                return line.strip()
        return "No summary found"
