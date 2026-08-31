def register(mcp):
    @mcp.tool()
    def probe_pylint_run_tests(repo_path: str, keyword: str = "") -> str:
        """Run pylint's pytest suite (tests/) in *repo_path*, optionally filtered
        by *keyword* (passed to pytest -k). Returns combined stdout/stderr,
        truncated to the last 8000 characters so large failure dumps don't
        blow out the caller's context.

        Use this to validate a change to pylint/lint/*.py against pylint's own
        test suite before trusting it — e.g. keyword="ignore" to run tests
        related to ignore-paths/ignore-patterns handling.
        """
        import subprocess

        cmd = ["python", "-m", "pytest", "tests/"]
        if keyword:
            cmd += ["-k", keyword]
        try:
            result = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, timeout=600
            )
        except subprocess.TimeoutExpired:
            return "TIMEOUT after 600s running: " + " ".join(cmd)

        output = result.stdout + "\n" + result.stderr
        if len(output) > 8000:
            output = output[-8000:]
        return f"exit={result.returncode}\n{output}"
