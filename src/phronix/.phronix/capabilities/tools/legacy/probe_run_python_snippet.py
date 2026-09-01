import json
import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def probe_run_python_snippet(repo_root: str, code: str, timeout: int = 120) -> str:
        """Run *code* as a python script inside *repo_root* (via `python -c`)
        and return JSON {status, ok, exit_code, output}. ok is True iff the
        process exited 0. Use this to reproduce a reported bug from an
        issue's minimal snippet, or to re-check that snippet after a fix
        (e.g. calling itermonomials(...) and printing the result to confirm
        expected terms are present)."""
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return json.dumps(
            {
                "status": "ok",
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "output": (proc.stdout + proc.stderr)[-4000:],
            }
        )
