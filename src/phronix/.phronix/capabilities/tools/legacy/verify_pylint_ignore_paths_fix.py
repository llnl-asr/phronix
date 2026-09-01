def register(mcp):
    import subprocess
    import os
    import tempfile
    import shutil
    
    @mcp.tool()
    def verify_pylint_ignore_paths_fix(repo_path: str = ".") -> str:
        """Verify that pylint correctly ignores paths when using --recursive=y.
        
        Creates a test directory structure, configures ignore-paths, and runs
        pylint to verify that ignored paths are excluded from the output.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Status message with verification results
        """
        # Create temporary test structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure: test/ignored/file.py and test/checked/file.py
            ignored_dir = os.path.join(tmpdir, "test", "ignored")
            checked_dir = os.path.join(tmpdir, "test", "checked")
            os.makedirs(ignored_dir)
            os.makedirs(checked_dir)
            
            # Create Python files with intentional issues
            ignored_file = os.path.join(ignored_dir, "bad.py")
            checked_file = os.path.join(checked_dir, "bad.py")
            
            bad_code = "x=1+2  # bad formatting\\n"
            
            with open(ignored_file, 'w') as f:
                f.write(bad_code)
            with open(checked_file, 'w') as f:
                f.write(bad_code)
            
            # Run pylint with ignore-paths
            result = subprocess.run(
                [
                    "python", "-m", "pylint",
                    "--recursive=y",
                    f"--ignore-paths=^{os.path.join(tmpdir, 'test', 'ignored')}/.*$".replace(os.sep, '/'),
                    os.path.join(tmpdir, "test")
                ],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            # Check that ignored path is not in output
            if "ignored" in result.stdout or "ignored" in result.stderr:
                return f"FAIL: Ignored path appeared in output:\\n{result.stdout}\\n{result.stderr}"
            
            # Check that non-ignored path is in output  
            if "checked" not in result.stdout and "checked" not in result.stderr:
                return f"WARN: Expected path 'checked' not found in output (might be OK if no issues):\\n{result.stdout}\\n{result.stderr}"
            
            return f"SUCCESS: Verification passed. Ignored paths correctly excluded."
    