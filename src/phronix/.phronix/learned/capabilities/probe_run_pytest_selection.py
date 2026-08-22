def register(mcp):
    import subprocess

    @mcp.tool()
    def probe_run_pytest_selection(repo_path: str, test_targets: str, keyword: str = "") -> str:
        """Run `python -m pytest <test_targets> [-k keyword] -q` inside
        *repo_path* and return the tail of stdout/stderr (pass/fail summary
        line plus any failures). test_targets is a space-separated string of
        paths, e.g. 'tests/lint/unittest_expand_modules.py tests/test_self.py'.
        Use this to check a candidate fix doesn't regress existing tests."""
        cmd = ["python", "-m", "pytest"] + test_targets.split()
        if keyword:
            cmd += ["-k", keyword]
        cmd.append("-q")
        try:
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True,
                                  text=True, timeout=300)
        except Exception as e:
            return f"ERROR: {e}"
        tail = "\n".join((res.stdout + res.stderr).splitlines()[-60:])
        return f"exit={res.returncode}\n{tail}"
