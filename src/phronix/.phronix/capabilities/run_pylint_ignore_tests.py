"""Run pylint test suite for ignore-paths functionality.

Executes the repository's tests related to ignore-paths and recursive mode
to verify the fix works correctly.
"""

import subprocess
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def run_pylint_ignore_tests(repo_path: str) -> str:
        """Run pylint tests for ignore-paths and recursive mode.
        
        Runs the test suite focusing on ignore-paths and recursive functionality
        to verify the fix passes tests.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Test results and summary
        """
        repo = Path(repo_path)
        if not repo.exists():
            return f"Error: Repository path not found: {repo_path}"
        
        # Run tests related to ignore paths
        test_commands = [
            # Run specific test methods
            ["python", "-m", "pytest", "-xvs", "tests/test_self.py::TestRunTC::test_ignore_path_recursive"],
            ["python", "-m", "pytest", "-xvs", "tests/test_self.py::TestRunTC::test_recursive_current_dir"],
        ]
        
        results = []
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                results.append({
                    "command": " ".join(cmd),
                    "returncode": result.returncode,
                    "output": result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout,
                    "stderr": result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "command": " ".join(cmd),
                    "returncode": -1,
                    "output": "",
                    "stderr": "Test timed out after 120 seconds"
                })
            except Exception as e:
                results.append({
                    "command": " ".join(cmd),
                    "returncode": -1,
                    "output": "",
                    "stderr": f"Error running test: {e}"
                })
        
        # Format output
        output_lines = ["Test Results:", "=" * 60]
        for r in results:
            output_lines.append(f"\nCommand: {r['command']}")
            output_lines.append(f"Return code: {r['returncode']}")
            if r['returncode'] == 0:
                output_lines.append("Status: PASSED ✓")
            else:
                output_lines.append("Status: FAILED ✗")
                output_lines.append(f"Output: {r['output']}")
                output_lines.append(f"Stderr: {r['stderr']}")
        
        return "\n".join(output_lines)
