def register(mcp):
    @mcp.tool()
    def run_pylint_tests(repo_root: str, test_pattern: str = "") -> str:
        """Run the pylint test suite to verify no regressions from the fix.
        
        Args:
            repo_root: Path to the pylint repository root
            test_pattern: Optional pattern to filter tests (e.g., "test_expand" or "test_ignore")
            
        Returns:
            JSON with test results summary
        """
        import os
        import json
        import subprocess
        
        # Run pytest on the tests directory
        if test_pattern:
            cmd = ["pytest", "-xvs", "-k", test_pattern, "tests/"]
        else:
            # Run all tests (this might take a while)
            cmd = ["pytest", "-x", "tests/"]
        
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        output = result.stdout + result.stderr
        
        # Parse results
        passed = "passed" in output.lower()
        failed = result.returncode != 0
        
        # Extract summary line if present
        summary_line = ""
        for line in output.split('\\n'):
            if 'passed' in line.lower() or 'failed' in line.lower():
                if '==' in line or 'PASSED' in line or 'FAILED' in line:
                    summary_line = line.strip()
        
        return json.dumps({
            "status": "pass" if not failed else "fail",
            "return_code": result.returncode,
            "test_pattern": test_pattern if test_pattern else "all tests",
            "summary": summary_line if summary_line else "see output",
            "output_tail": output[-1000:] if len(output) > 1000 else output
        }, indent=2)
