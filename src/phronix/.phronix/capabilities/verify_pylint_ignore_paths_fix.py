def register(mcp):
    import subprocess
    import os
    
    @mcp.tool()
    def verify_pylint_ignore_paths_fix(repo_path: str) -> str:
        """Verify that pylint --recursive=y now respects ignore-paths configuration.
        
        Runs the repository's test suite focusing on ignore-paths tests.
        
        Args:
            repo_path: Path to the pylint repository
            
        Returns:
            str: Test results summary
        """
        # Run specific tests for ignore-paths with recursive mode
        test_commands = [
            ["python", "-m", "pytest", "tests/test_self.py::TestRunTC::test_ignore_path_recursive", "-xvs"],
            ["python", "-m", "pytest", "tests/lint/unittest_lint.py::test_recursive_ignore", "-xvs"],
        ]
        
        results = []
        for cmd in test_commands:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            test_name = cmd[3].split("::")[-1]
            if result.returncode == 0:
                results.append(f"{test_name}: PASSED")
            else:
                results.append(f"{test_name}: FAILED\\n{result.stdout[-500:]}")
        
        return "\\n".join(results)
