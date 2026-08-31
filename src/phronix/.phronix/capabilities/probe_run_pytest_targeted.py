import subprocess
import sys
import json


def register(mcp):
    @mcp.tool()
    def probe_run_pytest_targeted(target: str, cwd: str = "", extra_args: str = "") -> str:
        """Run `python -m pytest <target> <extra_args>` in *cwd* (defaults to current
        directory) and return a JSON summary: {passed, failed, errors, returncode,
        tail} where tail is the last portion of combined output (for diagnosing
        failures without flooding context).
        """
        import os

        workdir = cwd or os.getcwd()
        cmd = [sys.executable, "-m", "pytest", target, "-q"]
        if extra_args:
            cmd += extra_args.split()
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=300)
        output = proc.stdout + proc.stderr
        tail = "\n".join(output.strip().splitlines()[-40:])
        return json.dumps(
            {
                "returncode": proc.returncode,
                "tail": tail,
            }
        )
