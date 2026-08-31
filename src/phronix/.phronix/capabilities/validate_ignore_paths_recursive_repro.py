import subprocess
import sys
import tempfile
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def validate_ignore_paths_recursive_repro(pylint_executable: str = "") -> str:
        """Create a temp dir with a namespace package (no __init__.py) containing
        a loose .py file under a 'gen' subdirectory, then run
        `pylint --recursive=y --ignore-paths='^.*gen/.*$'` against it (using the
        given interpreter's -m pylint, or the given pylint_executable if set).

        Reports whether the ignored file was actually skipped (bug fixed) or
        still linted (bug present).
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            gen = root / "gen"
            gen.mkdir(parents=True)
            (root / "good.py").write_text("x = 1\n")
            (gen / "bad.py").write_text("import os\nimport os\n")

            cmd = (
                [pylint_executable]
                if pylint_executable
                else [sys.executable, "-m", "pylint"]
            )
            cmd += [
                "--recursive=y",
                "--ignore-paths=^.*gen/.*$",
                str(root),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = proc.stdout + proc.stderr
            bad_seen = "bad.py" in output or "bad" in output
            good_seen = "good.py" in output or "good" in output
            return (
                f"exit_code={proc.returncode}\n"
                f"gen/bad.py referenced in output: {bad_seen} "
                "(should be False if ignore-paths is respected)\n"
                f"good.py referenced/checked: {good_seen}\n"
                f"--- raw output ---\n{output}"
            )
