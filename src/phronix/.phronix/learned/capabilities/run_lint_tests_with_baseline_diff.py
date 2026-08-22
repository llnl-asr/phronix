import subprocess


def _run(repo_path, targets):
    proc = subprocess.run(
        ["python", "-m", "pytest", *targets, "-q"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.stdout + proc.stderr


def register(mcp):
    @mcp.tool()
    def run_lint_tests_with_baseline_diff(
        repo_path: str, targets: str = "tests/lint"
    ) -> str:
        """Run `python -m pytest <targets> -q` in repo_path (targets is a
        space-separated list of pytest args/paths, default 'tests/lint'),
        then git-stash any uncommitted changes and re-run the same command
        to get the baseline (pre-fix) result, then git-stash-pop to restore
        the working tree. Returns both outputs' summary lines so the caller
        can see which failures are pre-existing versus newly introduced.

        Requires a clean-enough git state that `git stash` / `git stash pop`
        round-trip safely; only uncommitted changes are stashed and restored.
        """
        target_list = targets.split()
        with_fix = _run(repo_path, target_list)

        subprocess.run(["git", "stash"], cwd=repo_path, capture_output=True, text=True)
        try:
            baseline = _run(repo_path, target_list)
        finally:
            subprocess.run(
                ["git", "stash", "pop"], cwd=repo_path, capture_output=True, text=True
            )

        def tail(s, n=15):
            lines = s.strip().splitlines()
            return "\n".join(lines[-n:])

        return (
            "=== WITH FIX ===\n"
            + tail(with_fix)
            + "\n\n=== BASELINE (git stash) ===\n"
            + tail(baseline)
        )
