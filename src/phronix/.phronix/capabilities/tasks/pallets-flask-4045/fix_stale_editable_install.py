import subprocess, sys, os

def register(mcp):
    @mcp.tool()
    def fix_stale_editable_install(repo_root: str) -> str:
        """Ensure `import flask` resolves inside repo_root; reinstall editable if it doesn't."""
        check = subprocess.run(
            [sys.executable, "-c", "import flask; print(flask.__file__)"],
            cwd=repo_root, capture_output=True, text=True,
        )
        resolved = check.stdout.strip()
        if resolved and os.path.realpath(resolved).startswith(os.path.realpath(repo_root)):
            return f"OK: flask already resolves inside repo_root ({resolved})"
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", repo_root, "--no-deps", "--quiet"],
            cwd=repo_root, capture_output=True, text=True,
        )
        recheck = subprocess.run(
            [sys.executable, "-c", "import flask; print(flask.__file__)"],
            cwd=repo_root, capture_output=True, text=True,
        )
        return (
            f"reinstalled editable (rc={install.returncode})\n"
            f"stdout={install.stdout}\nstderr={install.stderr}\n"
            f"post-check: {recheck.stdout.strip()} err={recheck.stderr.strip()}"
        )
