def register(mcp):
    import subprocess
    import os
    
    @mcp.tool()
    def verify_recursive_ignore_tests(repo_path: str) -> dict:
        """Run tests related to recursive mode and ignore-paths functionality.
        
        Args:
            repo_path: Path to the repository root
            
        Returns:
            Dictionary with test results including passed/failed counts
        """
        os.chdir(repo_path)
        
        # Run the specific test for ignore_path_recursive
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_self.py::TestRunTC::test_ignore_path_recursive", "-xvs"],
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        passed = "passed" in output.lower()
        
        return {
            "status": "pass" if result.returncode == 0 else "fail",
            "returncode": result.returncode,
            "test_passed": passed,
            "output_summary": output[-500:] if len(output) > 500 else output
        }
