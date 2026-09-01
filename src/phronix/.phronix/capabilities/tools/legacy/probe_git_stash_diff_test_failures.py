import subprocess

def _run_pytest(repo_path, test_path, k_filter):
    cmd = ["python", "-m", "pytest", test_path, "-q"]
    if k_filter:
        cmd += ["-k", k_filter]
    out = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=900)
    return out.returncode, (out.stdout + out.stderr)

def register(mcp):
    @mcp.tool()
    def probe_git_stash_diff_test_failures(repo_path: str, test_path: str, k_filter: str = "") -> str:
        """Run the given pytest selection with the working tree's current
        uncommitted changes applied (patched), then git stash them and rerun
        (baseline), then git stash pop to restore. Returns a summary comparing
        return codes so pre-existing failures aren't mistaken for regressions."""
        try:
            patched_rc, patched_out = _run_pytest(repo_path, test_path, k_filter)

            stash = subprocess.run(["git", "stash"], cwd=repo_path, capture_output=True, text=True, timeout=60)
            stashed = "No local changes to save" not in stash.stdout

            baseline_rc, baseline_out = _run_pytest(repo_path, test_path, k_filter)

            if stashed:
                subprocess.run(["git", "stash", "pop"], cwd=repo_path, capture_output=True, text=True, timeout=60)

            return (
                f"patched_returncode={patched_rc}\n"
                f"baseline_returncode={baseline_rc}\n"
                f"patched_tail:\n{chr(10).join(patched_out.splitlines()[-20:])}\n"
                f"baseline_tail:\n{chr(10).join(baseline_out.splitlines()[-20:])}"
            )
        except Exception as e:
            return f"error: {e}"
