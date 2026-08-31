import subprocess

def register(mcp):
    @mcp.tool()
    def probe_run_pytest_subset(repo_path: str, test_path: str, k_filter: str = "") -> str:
        """Run `pytest <test_path> -k <k_filter> -q` inside repo_path and return
        the captured stdout/stderr tail plus return code. test_path is relative
        to repo_path (e.g. 'tests/lint/unittest_lint.py'). k_filter may be empty
        to run the whole file."""
        cmd = ["python", "-m", "pytest", test_path, "-q"]
        if k_filter:
            cmd += ["-k", k_filter]
        try:
            out = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, timeout=600,
            )
        except Exception as e:
            return f"error: {e}"
        tail = "\n".join((out.stdout + out.stderr).splitlines()[-60:])
        return f"returncode={out.returncode}\n{tail}"
