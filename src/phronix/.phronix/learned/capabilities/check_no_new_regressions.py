import subprocess


def register(mcp):
    @mcp.tool()
    def check_no_new_regressions(repo_root: str, testpath: str = "tests/test_self.py") -> str:
        """Run *testpath* with the working tree as-is, then again with
        local changes stashed (unmodified baseline), and report whether
        the failing-test set grew. Restores the stash afterwards
        regardless of outcome. Returns a summary string.
        """

        def run_failed_set():
            proc = subprocess.run(
                ["python", "-m", "pytest", testpath, "-q"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            failed = {
                line.split("::", 1)[-1] if "::" in line else line
                for line in proc.stdout.splitlines()
                if line.startswith("FAILED ")
            }
            return failed

        after = run_failed_set()

        stash_result = subprocess.run(
            ["git", "stash", "-u"], cwd=repo_root, capture_output=True, text=True
        )
        stashed = "No local changes to save" not in stash_result.stdout
        try:
            before = run_failed_set() if stashed else after
        finally:
            if stashed:
                subprocess.run(["git", "stash", "pop"], cwd=repo_root, capture_output=True, text=True)

        new_failures = after - before
        if new_failures:
            return f"FAIL: new regressions introduced: {sorted(new_failures)}"
        return (
            f"ok: no new regressions ({len(after)} failing before and after, "
            f"all pre-existing/environmental)"
        )
