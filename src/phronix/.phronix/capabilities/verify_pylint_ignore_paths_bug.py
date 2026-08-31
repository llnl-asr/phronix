def register(mcp):
    import subprocess
    import tempfile
    import os
    from pathlib import Path
    
    @mcp.tool()
    def verify_pylint_ignore_paths_bug(repo_path: str) -> str:
        """Verify that pylint --recursive=y currently ignores ignore-paths configuration.
        
        Creates a minimal test case with an ignored path pattern and checks if files
        matching that pattern are still being linted in recursive mode.
        
        Args:
            repo_path: Path to the pylint repository
            
        Returns:
            str: "bug confirmed" if files matching ignore-paths are linted, 
                 "bug not found" if they are correctly ignored
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            gen_dir = Path(tmpdir) / "src" / "gen"
            gen_dir.mkdir(parents=True)
            
            # Create a file with a pylint violation
            test_file = gen_dir / "test.py"
            test_file.write_text("import re  # Unused import\n")
            
            # Create pyproject.toml with ignore-paths
            config_file = Path(tmpdir) / "pyproject.toml"
            config_file.write_text("""[tool.pylint.MASTER]
ignore-paths = [
    "^src/gen/.*$",
]
""")
            
            # Run pylint with recursive mode
            result = subprocess.run(
                ["python", "-m", "pylint", "--recursive=y", "src/"],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            # Check if the ignored file was linted
            if "src/gen/test.py" in result.stdout or "src\\gen\\test.py" in result.stdout:
                return "bug confirmed: files in src/gen/ were linted despite ignore-paths"
            else:
                return "bug not found: files in src/gen/ were correctly ignored"
