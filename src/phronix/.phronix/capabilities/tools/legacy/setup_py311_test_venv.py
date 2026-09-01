def register(mcp):
    import subprocess

    @mcp.tool()
    def setup_py311_test_venv(repo_path: str, venv_dir: str) -> str:
        """Create a Python 3.11 virtualenv at venv_dir, then `pip install -e
        repo_path` plus `pytest<8` into it. Use this when the ambient
        interpreter (e.g. Python 3.13) is too new for the project's pinned
        pytest/ast usage and the test suite errors out on collection.
        Returns the venv's python path on success, or the failing command's
        output on error."""
        steps = [
            ["python3.11", "-m", "venv", venv_dir],
            [f"{venv_dir}/bin/pip", "install", "-e", repo_path, "pytest<8"],
        ]
        for cmd in steps:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode != 0:
                return f"FAILED: {' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
        return f"{venv_dir}/bin/python"
