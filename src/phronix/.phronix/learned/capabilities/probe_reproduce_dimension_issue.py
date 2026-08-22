import json
import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def probe_reproduce_dimension_issue(repo_root: str) -> str:
        """Reproduce the sympy exp()-of-dimensionless-ratio dimension bug by
        calling SI._collect_factor_and_dimension on
        100 + exp(second/(ohm*farad)). Returns JSON
        {status, ok, output} where ok=True means no exception was raised.
        """
        script = (
            "from sympy import exp\n"
            "from sympy.physics import units\n"
            "from sympy.physics.units.systems.si import SI\n"
            "expr = 100 + exp(units.second / (units.ohm * units.farad))\n"
            "try:\n"
            "    result = SI._collect_factor_and_dimension(expr)\n"
            "    print('OK', result)\n"
            "except Exception as e:\n"
            "    print('FAIL', type(e).__name__, e)\n"
            "    raise\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        ok = proc.returncode == 0 and "OK" in proc.stdout
        return json.dumps(
            {
                "status": "ok",
                "ok": ok,
                "output": (proc.stdout + proc.stderr)[-4000:],
            }
        )
