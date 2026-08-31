import subprocess
import sys
import tempfile
import os


def register(mcp):
    @mcp.tool()
    def probe_run_pylint_snippet(code: str, args: str = "", cwd: str = "") -> str:
        """Write *code* to a temp .py file and run `python -m pylint <args> <file>` in *cwd*
        (defaults to current directory). Returns JSON with stdout, stderr, and returncode.
        Useful for reproducing a pylint message/behavior described in an issue without
        touching the repository's own test files.
        """
        import json

        workdir = cwd or os.getcwd()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=workdir
        ) as f:
            f.write(code)
            path = f.name
        try:
            cmd = [sys.executable, "-m", "pylint"] + (args.split() if args else []) + [path]
            proc = subprocess.run(
                cmd, cwd=workdir, capture_output=True, text=True, timeout=120
            )
            return json.dumps(
                {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "returncode": proc.returncode,
                    "file": path,
                }
            )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
