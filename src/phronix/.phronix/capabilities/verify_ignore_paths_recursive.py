import subprocess

def register(mcp):
    @mcp.tool()
    def verify_ignore_paths_recursive(repo_root: str) -> str:
        """Run pytest tests/lint/unittest_expand_modules.py tests/test_self.py -k
        "ignore_path or ignore_pattern or recursive or expand_modules" in *repo_root*
        and return the captured output (last 4000 chars) plus pass/fail summary."""
        proc = subprocess.run(
            [
                "python3", "-m", "pytest",
                "tests/lint/unittest_expand_modules.py",
                "tests/test_self.py",
                "-k", "ignore_path or ignore_pattern or recursive or expand_modules",
                "-q",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = (proc.stdout + proc.stderr)[-4000:]
        status = "ok: all passed" if proc.returncode == 0 else f"fail: returncode={proc.returncode}"
        return f"{status}\n{out}"
