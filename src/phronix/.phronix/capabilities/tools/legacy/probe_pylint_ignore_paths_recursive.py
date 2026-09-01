import json
import subprocess
import sys
import tempfile
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def probe_pylint_ignore_paths_recursive(
        pylint_path: str,
        ignored_subdir: str = "gen",
        ignore_paths_pattern: str = "^gen/.*$",
    ) -> str:
        """Reproduce/verify pylint's --recursive=y handling of ignore-paths.

        Builds a temp project tree with a normal package and an
        ``ignored_subdir`` (default "gen") both containing a trivial
        .py module with an obvious lint issue (unused import). Writes a
        pyproject.toml setting ``ignore-paths`` to *ignore_paths_pattern*.
        Runs ``python -m pylint --recursive=y .`` from *pylint_path*
        (the pylint checkout to test, e.g. its repo root, used via
        PYTHONPATH so the checkout's code is exercised) against the temp
        tree and reports which modules appear as linted (i.e. produced a
        message) vs which were excluded.

        Returns JSON: {status, linted_modules, excluded_modules,
        ignored_subdir_leaked (bool: True if the ignored subdir's module
        still got linted, meaning the bug is present), raw_stdout}.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            normal_dir = root / "normal"
            normal_dir.mkdir()
            (normal_dir / "__init__.py").write_text("")
            (normal_dir / "mod_normal.py").write_text("import os\n")

            ignored_dir = root / ignored_subdir
            ignored_dir.mkdir()
            (ignored_dir / "__init__.py").write_text("")
            (ignored_dir / "mod_ignored.py").write_text("import sys\n")

            (root / "pyproject.toml").write_text(
                "[tool.pylint.MASTER]\n"
                f'ignore-paths = ["{ignore_paths_pattern}"]\n'
            )

            env_pythonpath = pylint_path
            proc = subprocess.run(
                [sys.executable, "-m", "pylint", "--recursive=y", "."],
                cwd=str(root),
                capture_output=True,
                text=True,
                env={"PYTHONPATH": env_pythonpath},
            )
            out = proc.stdout

            linted = []
            excluded = []
            for name, path in (
                ("normal.mod_normal", "mod_normal.py"),
                (f"{ignored_subdir}.mod_ignored", "mod_ignored.py"),
            ):
                if path in out:
                    linted.append(name)
                else:
                    excluded.append(name)

            ignored_leaked = "mod_ignored.py" in out

            return json.dumps(
                {
                    "status": "ok",
                    "linted_modules": linted,
                    "excluded_modules": excluded,
                    "ignored_subdir_leaked": ignored_leaked,
                    "raw_stdout": out,
                }
            )
