import subprocess


def register(mcp):
    @mcp.tool()
    def run_pytest_file(repo_dir: str, test_path: str, extra_args: str = "-q") -> str:
        """Run pytest on test_path (relative to repo_dir) with optional extra_args.
        Returns JSON: {status, returncode, stdout_tail, stderr_tail}."""
        import json

        cmd = ["python", "-m", "pytest", test_path] + extra_args.split()
        try:
            proc = subprocess.run(
                cmd, cwd=repo_dir, capture_output=True, text=True, timeout=300
            )
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})

        return json.dumps(
            {
                "status": "ok",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
