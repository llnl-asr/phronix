import shutil
import subprocess
from pathlib import Path

SPEC = {
    "kind": "skill",
    "target": "normalize-ignore-paths",
    "claim": "pylint --recursive=y ignores ignore-paths patterns defined in pyproject.toml",
    "assumptions": [
        {"name": "pylint_installed", "detail": "pylint is on PATH", "check": lambda ctx: shutil.which("pylint") is not None},
        {"name": "src_exists", "detail": "src directory exists", "check": lambda ctx: Path("src").exists()}
    ],
    "inputs": [
        {"name": "pylint_output", "required": True, "resolve": lambda ctx: subprocess.run(["pylint", "--recursive=y", "src/"], capture_output=True, text=True).stdout}
    ],
    "constraints": [
        {"name": "ignore_path_violated", "detail": "ignore-paths patterns are ignored; output contains warnings from ignored files", "check": lambda ctx: any("src\\gen\\" in line for line in ctx["pylint_output"].splitlines())}
    ],
    "invariants": [],
    "outputs": [
        {"name": "output_nonempty", "check": lambda ctx: len(ctx["pylint_output"]) > 0}
    ]
}
