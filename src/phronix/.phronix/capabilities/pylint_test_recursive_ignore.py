"""Test pylint's recursive mode respects ignore-paths configuration.

Creates a test structure matching the issue #7080 scenario and verifies that files
in directories matching ignore-paths patterns are actually ignored.
"""

from pathlib import Path
import subprocess
import tempfile
import shutil

def register(mcp):
    @mcp.tool()
    def pylint_test_recursive_ignore(repo_root: str) -> str:
        """Test that pylint --recursive=y respects ignore-paths configuration.
        
        Args:
            repo_root: Path to the pylint repository root
            
        Returns:
            Test result with pass/fail status and details
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir) / "test_project"
            test_root.mkdir()
            
            # Create directory structure matching issue #7080
            src_dir = test_root / "src"
            src_dir.mkdir()
            
            gen_dir = src_dir / "gen"
            gen_dir.mkdir()
            
            # Create a valid Python file in src/
            (src_dir / "main.py").write_text("print('hello')\n")
            
            # Create a file with deliberate style violations in src/gen/
            (gen_dir / "generated.py").write_text(
                "x=1\ny=2\nz=3\n"  # Missing spaces around =
            )
            
            # Create pyproject.toml with ignore-paths
            (test_root / "pyproject.toml").write_text("""
[tool.pylint.MASTER]
ignore-paths = [
    "^src/gen/.*$",
]
""")
            
            # Run pylint with --recursive=y from project root
            result = subprocess.run(
                ["python", "-m", "pylint", "--recursive=y", "src/"],
                cwd=test_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if src/gen/generated.py appears in output
            output = result.stdout + result.stderr
            
            if "src/gen/generated.py" in output or "src\\gen\\generated.py" in output:
                return f"FAIL: Files in src/gen/ were NOT ignored despite ignore-paths pattern.\n\nOutput:\n{output}"
            
            if "src/main.py" in output or "src\\main.py" in output or result.returncode == 0:
                return "PASS: ignore-paths correctly excluded src/gen/ while processing src/main.py"
            
            return f"INCONCLUSIVE: Neither src/gen nor src/main appeared in output.\n\nReturn code: {result.returncode}\nOutput:\n{output}"
