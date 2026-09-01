import subprocess


def register(mcp):
    @mcp.tool()
    def python_repro_snippet(repo_dir: str, code: str, timeout: int = 30) -> str:
        """Execute `code` with `python -c` inside repo_dir (so local packages
        import correctly) and report the outcome. Useful for quick manual
        repro/verification checks after a code change.
        Returns JSON: {status, returncode, stdout, stderr}."""
        import json

        try:
            proc = subprocess.run(
                ["python", "-c", code],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})

        return json.dumps(
            {
                "status": "ok",
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-2000:],
            }
        )
