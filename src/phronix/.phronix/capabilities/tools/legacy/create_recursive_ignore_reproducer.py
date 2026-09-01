"""Capability to create a reproducer test for the recursive ignore-paths issue."""

def register(mcp):
    import os
    import tempfile
    import shutil
    
    @mcp.tool()
    def create_recursive_ignore_reproducer(repo_path: str) -> str:
        """Create test directory structure and run pylint to reproduce the bug.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            JSON string with test results
        """
        import json
        import subprocess
        
        # Create a temporary test directory
        test_dir = os.path.join(repo_path, "test_recursive_ignore_bug")
        
        try:
            # Clean up if it exists
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
            
            # Create directory structure: test_recursive_ignore_bug/src/gen/
            gen_dir = os.path.join(test_dir, "src", "gen")
            os.makedirs(gen_dir, exist_ok=True)
            
            # Create a file that should be ignored
            bad_file = os.path.join(gen_dir, "bad.py")
            with open(bad_file, 'w') as f:
                f.write('# This should be ignored\\n')
                f.write('x = "a very long line that exceeds eighty characters limit for pylint style checks"\\n')
            
            # Create pyproject.toml with ignore-paths
            pyproject = os.path.join(test_dir, "pyproject.toml")
            with open(pyproject, 'w') as f:
                f.write('[tool.pylint.MASTER]\\n')
                f.write('ignore-paths = ["^.*/src/gen/.*$"]\\n')
            
            # Run pylint with --recursive=y
            result = subprocess.run(
                ["python", "-m", "pylint", "--recursive=y", "src/"],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if the ignored file was linted (bug) or not (fixed)
            bug_present = "gen/bad.py" in result.stdout or "gen/bad.py" in result.stderr
            
            return json.dumps({
                "bug_reproduced": bug_present,
                "test_dir": test_dir,
                "returncode": result.returncode,
                "output_snippet": (result.stdout + result.stderr)[:500]
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)})
