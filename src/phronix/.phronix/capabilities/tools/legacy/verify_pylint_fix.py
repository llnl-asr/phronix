"""Verify that the fix resolves the ignore-paths bug.

Re-runs the test case to confirm that ignore-paths now works correctly
with --recursive=y after applying the fix.
"""

import subprocess
import tempfile
import os
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def verify_pylint_fix(repo_path: str) -> str:
        """Verify the fix resolves the ignore-paths bug with --recursive=y.
        
        Creates the same test case as before and confirms that files matching
        ignore-paths are now properly ignored.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Verification result message
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
            
            # Create a good file in the root
            good_file = test_dir / "good.py"
            good_file.write_text("""
def good_function():
    x = 1 + 2
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
            
            # Check results
            output = result.stdout + result.stderr
            
            has_gen_file = "gen/test.py" in output or "gen\\test.py" in output
            has_good_file = "good.py" in output
            
            if has_gen_file:
                return f"FAIL: gen/test.py was linted (should be ignored). Output:\n{output[:500]}"
            elif not has_good_file:
                return f"UNCLEAR: Neither file was linted. May be config issue. Output:\n{output[:500]}"
            else:
                return f"SUCCESS: Fix verified! gen/test.py was ignored, good.py was linted. Return code: {result.returncode}"
