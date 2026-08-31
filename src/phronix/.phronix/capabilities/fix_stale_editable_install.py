import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def fix_stale_editable_install(repo_root: str) -> str:
        """Reinstall the package at *repo_root* in editable mode (pip install -e . --no-deps).

        Use this when `python -c "import <pkg>"` resolves to a file path
        outside *repo_root* (e.g. another task's checkout), which happens
        when a stale .pth/egg-link from a previous editable install shadows
        the current repo on sys.path. Symptom: imports fail or behave
        unexpectedly with errors that reference an unrelated directory,
        even though the code under test looks correct. This is an
        environment problem, not a code bug — do not "fix" it by editing
        source to work around the wrong import.

        Returns the pip output.
        """
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        out = result.stdout + result.stderr
        if result.returncode != 0:
            return f"FAILED (exit {result.returncode}):\n{out}"
        return f"OK: reinstalled editable package from {repo_root}\n{out}"
