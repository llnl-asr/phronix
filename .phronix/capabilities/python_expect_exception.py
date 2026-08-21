import subprocess
import sys

def register(mcp):
    @mcp.tool()
    def python_expect_exception(code: str, expected_exception: str = "", cwd: str = ".", timeout: int = 30) -> str:
        """Run *code* with `python -c` and report whether it raised *expected_exception*.

        *expected_exception* is the exception class name (e.g. "ValueError"); leave
        empty to just report what happened. Returns stdout/stderr and a verdict.
        """
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return "error: timed out"

        stderr = proc.stderr
        raised = None
        for line in reversed(stderr.strip().splitlines()):
            if ":" in line and line[0].isalpha() and not line.startswith(" "):
                raised = line.split(":")[0].strip()
                break

        verdict = "unknown"
        if expected_exception:
            verdict = "pass" if raised == expected_exception else "fail"

        return (
            f"returncode: {proc.returncode}\n"
            f"raised: {raised}\n"
            f"verdict: {verdict}\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {stderr}"
        )
