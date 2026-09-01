"""Verify the pylint ignore-paths bug exists.

Creates a minimal test case to confirm that --recursive=y ignores the
ignore-paths configuration.
"""

import subprocess
import tempfile
import os
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def verify_pylint_ignore_paths_bug(repo_path: str) -> str:
        """Verify that pylint --recursive=y ignores ignore-paths configuration.
        
        Creates a test directory structure with files that should be ignored
        based on ignore-paths pattern, runs pylint recursively, and checks
        if the files are incorrectly linted.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Status message indicating if bug exists
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test directory structure
            test_dir = Path(tmpdir) / "test_project"
            test_dir.mkdir()
            
            gen_dir = test_dir / "gen"
            gen_dir.mkdir()
            
            # Create a Python file in gen/ that would trigger pylint errors
            test_file = gen_dir / "test.py"
            test_file.write_text("""
# This file has intentional style issues
def BadFunctionName():
    x=1+2  # Bad spacing
    return x
""")
            
            # Create pyproject.toml with ignore-paths
            config_file = test_dir / "pyproject.toml"
            config_file.write_text("""
[tool.pylint.MASTER]
ignore-paths = [
    "^gen/.*$",
]
""")
            
            # Run pylint recursively from test_dir
            result = subprocess.run(
                ["python", "-m", "pylint", "--recursive=y", "."],
                cwd=test_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if gen/test.py was linted (bug) or ignored (correct)
            output = result.stdout + result.stderr
            
            if "gen/test.py" in output or "gen\\test.py" in output:
                return f"BUG CONFIRMED: ignore-paths is being ignored. Pylint output:\n{output[:500]}"
            else:
                return f"Bug not reproduced or already fixed. Return code: {result.returncode}"
