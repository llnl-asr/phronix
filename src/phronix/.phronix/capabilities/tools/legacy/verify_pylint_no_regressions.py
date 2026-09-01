def register(mcp):
    import subprocess
    
    @mcp.tool()
    def verify_pylint_no_regressions(repo_path: str) -> str:
        """Verify that ignore functionality still works in non-recursive mode.
        
        Runs tests for --ignore, --ignore-patterns, and --ignore-paths in non-recursive mode.
        
        Args:
            repo_path: Path to the pylint repository
            
        Returns:
            str: Test results summary
        """
        # Run broader test suite for ignore functionality
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/lint/unittest_lint.py", "tests/test_self.py", "-k", "ignore", "-x"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return "All ignore-related tests PASSED"
        else:
            # Extract last part of output for debugging
            return f"Some tests FAILED (exit {result.returncode}):\\n{result.stdout[-1000:]}"
