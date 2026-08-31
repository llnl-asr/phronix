"""Validate that ignore-paths configuration works correctly with recursive scanning.

This capability creates a test scenario matching the reported issue:
- Sets up a pyproject.toml with ignore-paths patterns
- Runs pylint with --recursive=y
- Verifies that matched paths are actually ignored
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def validate_ignore_paths_fix(
        ignore_pattern: str = "^src/gen/.*$",
        test_dir_structure: str = "src/gen/test.py,src/main.py"
    ) -> str:
        """Validate ignore-paths works with --recursive=y.
        
        Args:
            ignore_pattern: The regex pattern to use in ignore-paths config
            test_dir_structure: Comma-separated paths to create for testing
            
        Returns:
            JSON string with validation results
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Create pyproject.toml with ignore-paths
                config_content = f"""[tool.pylint.MASTER]
ignore-paths = [
    "{ignore_pattern}",
]
"""
                (tmppath / "pyproject.toml").write_text(config_content)
                
                # Create test Python files
                for file_path in test_dir_structure.split(','):
                    file_path = file_path.strip()
                    full_path = tmppath / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write invalid Python to ensure pylint would complain if it checks
                    full_path.write_text("""
# Test file with intentional issues
class badClassName:  # invalid-name
    def BadMethod(x):  # invalid-name, missing-self
        pass
""")
                
                # Run pylint with --recursive=y
                result = subprocess.run(
                    ["pylint", "--recursive=y", "src/"],
                    cwd=tmppath,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Check if ignored files appear in output
                ignored_files = []
                checked_files = []
                
                for line in result.stdout.split('\n'):
                    if 'src/gen/' in line:
                        ignored_files.append(line.strip())
                    elif 'src/' in line and 'Module' in line:
                        checked_files.append(line.strip())
                
                # The fix is successful if no src/gen/ files appear in output
                success = len(ignored_files) == 0
                
                return json.dumps({
                    'status': 'completed',
                    'success': success,
                    'ignored_files_appeared': len(ignored_files),
                    'other_files_checked': len(checked_files),
                    'message': 'ignore-paths working correctly' if success else 'ignore-paths NOT respected',
                    'sample_output': result.stdout[:500] if result.stdout else '(empty)'
                }, indent=2)
                
        except subprocess.TimeoutExpired:
            return json.dumps({'status': 'timeout', 'message': 'pylint execution timeout'})
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})
