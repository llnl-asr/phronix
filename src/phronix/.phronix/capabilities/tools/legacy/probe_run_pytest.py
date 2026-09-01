import subprocess

def register(mcp):
    @mcp.tool()
    def probe_run_pytest(paths: str, cwd: str = ".", extra_args: str = "-q") -> str:
        """Run pytest on the given space-separated paths/modules (e.g. 'tests/lint/unittest_lint.py tests/lint/unittest_expand_modules.py') inside `cwd`, using pytest's own resolution. Returns exit code and the last portion of combined stdout/stderr so pass/fail and failure summaries are visible without flooding context.

        Args:
            paths: space-separated test paths, node ids, or module paths to pass to pytest.
            cwd: working directory to run pytest from (default: current directory).
            extra_args: additional pytest CLI args, e.g. "-q" or "-x -k something".
        """
        cmd = ["python", "-m", "pytest"] + extra_args.split() + paths.split()
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
        tail = (proc.stdout + "\n" + proc.stderr)[-6000:]
        return f"exit_code={proc.returncode}\n{tail}"

    return None
