"""Capability to run specific pylint tests for recursive ignore functionality."""

def register(mcp):
    import subprocess
    import os
    
    @mcp.tool()
    def run_pylint_recursive_tests(repo_path: str) -> str:
        """Run pytest tests for recursive ignore functionality.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            JSON string with test results
        """
        import json
        
        tests = [
            "tests/lint/unittest_lint.py::test_recursive_ignore",
            "tests/test_self.py::TestRunTC::test_ignore_path_recursive"
        ]
        
        results = {}
        for test in tests:
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", test, "-xvs"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                results[test] = {
                    "returncode": result.returncode,
                    "passed": result.returncode == 0,
                    "stdout": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
                    "stderr": result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                }
            except subprocess.TimeoutExpired:
                results[test] = {"error": "Test timed out"}
            except Exception as e:
                results[test] = {"error": str(e)}
        
        all_passed = all(r.get("passed", False) for r in results.values())
        
        return json.dumps({
            "all_passed": all_passed,
            "results": results
        }, indent=2)
