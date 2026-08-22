import subprocess

def register(mcp):
    @mcp.tool()
    def run_pylint_ignore_tests(repo_root: str, full_suite: bool = False) -> str:
        """Run pytest against pylint's ignore-focused unit tests
        (tests/lint/unittest_lint.py -k ignore) by default, or the full
        tests/lint/ suite when full_suite is True. Returns combined
        stdout+stderr tail."""
        target = "tests/lint/" if full_suite else "tests/lint/unittest_lint.py"
        args = ["python", "-m", "pytest", target, "-q"]
        if not full_suite:
            args += ["-k", "ignore"]
        r = subprocess.run(args, cwd=repo_root, capture_output=True, text=True, timeout=600)
        tail = (r.stdout + "\n" + r.stderr)[-6000:]
        return f"returncode={r.returncode}\n{tail}"
