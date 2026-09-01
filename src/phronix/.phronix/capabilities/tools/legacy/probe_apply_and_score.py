import subprocess
import sys

def register(mcp):
    @mcp.tool()
    def probe_apply_and_score(patch_text: str, test_selection: str, cwd: str = ".", timeout: int = 120) -> str:
        """Apply *patch_text* (unified diff, via `git apply`) then run *test_selection*
        (a pytest target string, e.g. "tests/test_blueprints.py -k dot") in *cwd*.

        Returns whether the patch applied cleanly and the pytest pass/fail summary,
        so a candidate approach's figure of merit can be measured in one call.
        """
        apply_proc = subprocess.run(
            ["git", "apply", "-"],
            input=patch_text,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if apply_proc.returncode != 0:
            return f"patch_applied: false\nerror: {apply_proc.stderr}"

        try:
            test_proc = subprocess.run(
                [sys.executable, "-m", "pytest", *test_selection.split()],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return "patch_applied: true\nerror: test run timed out"

        tail = "\n".join(test_proc.stdout.strip().splitlines()[-15:])
        return (
            f"patch_applied: true\n"
            f"returncode: {test_proc.returncode}\n"
            f"passed: {test_proc.returncode == 0}\n"
            f"summary_tail:\n{tail}"
        )
