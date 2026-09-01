def register(mcp):
    @mcp.tool()
    def test_recursive_ignore_paths(repo_root: str, test_dir: str) -> str:
        """Create a test case and verify that ignore-paths works with --recursive=y.
        
        Creates a minimal test directory structure with files that should be checked
        and files that should be ignored, then runs pylint with --recursive=y to
        verify the ignore-paths pattern is respected.
        
        Args:
            repo_root: Path to the pylint repository root (for running pylint)
            test_dir: Path to create test files (should be in scratch space)
            
        Returns:
            JSON with test results and verification status
        """
        import os
        import json
        import subprocess
        import shutil
        
        # Clean up test_dir if it exists
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        # Create test structure
        os.makedirs(os.path.join(test_dir, "src", "gen"), exist_ok=True)
        
        # Create a normal file that should be checked
        normal_file = os.path.join(test_dir, "src", "normal.py")
        with open(normal_file, 'w') as f:
            f.write("# This file should be checked\\n")
            f.write("x = 1\\n")
        
        # Create a file in gen/ that should be ignored
        ignored_file = os.path.join(test_dir, "src", "gen", "ignored.py")
        with open(ignored_file, 'w') as f:
            f.write("# This file should be ignored\\n")
            f.write("this is not valid python syntax!!!\\n")
        
        # Create pyproject.toml with ignore-paths config
        config_file = os.path.join(test_dir, "pyproject.toml")
        with open(config_file, 'w') as f:
            f.write('[tool.pylint.MASTER]\\n')
            f.write('ignore-paths = [\\n')
            f.write('  "^src/gen/.*$",\\n')
            f.write(']\\n')
        
        # Run pylint with --recursive=y
        pylint_cmd = [
            "python", "-m", "pylint",
            "--recursive=y",
            "src/"
        ]
        
        result = subprocess.run(
            pylint_cmd,
            cwd=test_dir,
            capture_output=True,
            text=True
        )
        
        # Check results
        output = result.stdout + result.stderr
        
        # The ignored file should NOT appear in output
        ignored_in_output = "src/gen/ignored.py" in output or "src\\\\gen\\\\ignored.py" in output
        
        # Check for the invalid syntax error that would occur if ignored.py was checked
        syntax_error_found = "not valid python" in output.lower() or "syntax" in output.lower()
        
        success = not ignored_in_output and not syntax_error_found
        
        return json.dumps({
            "status": "pass" if success else "fail",
            "test_dir": test_dir,
            "ignored_file_checked": ignored_in_output,
            "syntax_error_found": syntax_error_found,
            "output_sample": output[:500] if output else "(no output)",
            "verdict": "ignore-paths is respected with --recursive=y" if success else "ignore-paths NOT respected - ignored file was checked"
        }, indent=2)
