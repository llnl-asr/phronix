import subprocess
import os

def register(mcp):
    @mcp.tool()
    def probe_run_pylint_recursive(pylint_repo_path: str, cwd: str, target: str, extra_args: str = "") -> str:
        """Run `python -m pylint --recursive=y <target>` with PYTHONPATH set to pylint_repo_path.

        pylint_repo_path: absolute path to the pylint checkout whose pylint/ package should be used.
        cwd: absolute working directory to run the command from (e.g. a repro fixture dir).
        target: the pylint target argument (e.g. ".", "src/", "src/gen").
        extra_args: optional extra space-separated pylint args.

        Returns JSON: {status, returncode, stdout, stderr}.
        """
        import json
        env = os.environ.copy()
        env["PYTHONPATH"] = pylint_repo_path
        cmd = ["python", "-m", "pylint", "--recursive=y", target]
        if extra_args:
            cmd += extra_args.split()
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
        return json.dumps({
            "status": "ok",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })
