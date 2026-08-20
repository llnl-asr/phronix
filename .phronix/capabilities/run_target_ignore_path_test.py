import subprocess


def register(mcp):
    @mcp.tool()
    def run_target_ignore_path_test(repo_root: str) -> str:
        """Run
        tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir
        in <repo_root> with pytest and return its captured stdout+stderr
        tail along with the process return code.
        """
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir",
                "-q",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr)[-4000:]
        return f"returncode={result.returncode}\n{output}"
