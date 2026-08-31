import os
import shutil
import subprocess
import sys
import tempfile


def register(mcp):
    @mcp.tool()
    def probe_pylint_recursive_ignore_paths(repo_path: str) -> str:
        """Reproduce pylint issue 7080: --recursive=y ignores ignore-paths.

        Builds a scratch project with a pyproject.toml declaring
        [tool.pylint.MASTER] ignore-paths = ["^ignored/.*$"], containing a
        package `ignored/` with a lint-triggering file and a package `kept/`
        with a lint-triggering file. Runs `python -m pylint --recursive=y .`
        from within the pylint checkout at *repo_path* (must contain a
        `pylint` package importable via PYTHONPATH).

        Returns a JSON string: {status, bug_present, stdout, stderr,
        ignored_flagged (bool), kept_flagged (bool)}.
        """
        import json

        tmpdir = tempfile.mkdtemp(prefix="pylint7080_")
        try:
            os.makedirs(os.path.join(tmpdir, "ignored"))
            os.makedirs(os.path.join(tmpdir, "kept"))
            with open(os.path.join(tmpdir, "pyproject.toml"), "w") as f:
                f.write(
                    "[tool.pylint.MASTER]\n"
                    'ignore-paths = ["^ignored/.*$"]\n'
                )
            bad_code = "import os\nx=1\n"
            with open(os.path.join(tmpdir, "ignored", "bad.py"), "w") as f:
                f.write(bad_code)
            with open(os.path.join(tmpdir, "ignored", "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(tmpdir, "kept", "bad.py"), "w") as f:
                f.write(bad_code)
            with open(os.path.join(tmpdir, "kept", "__init__.py"), "w") as f:
                f.write("")

            env = dict(os.environ)
            env["PYTHONPATH"] = repo_path + os.pathsep + env.get("PYTHONPATH", "")

            proc = subprocess.run(
                [sys.executable, "-m", "pylint", "--recursive=y", "."],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            stdout = proc.stdout
            ignored_flagged = "ignored" in stdout and "bad.py" in stdout and (
                "ignored" + os.sep + "bad.py" in stdout or "ignored/bad.py" in stdout
            )
            kept_flagged = "kept/bad.py" in stdout or ("kept" + os.sep + "bad.py") in stdout

            return json.dumps(
                {
                    "status": "ok",
                    "bug_present": ignored_flagged,
                    "ignored_flagged": ignored_flagged,
                    "kept_flagged": kept_flagged,
                    "stdout": stdout,
                    "stderr": proc.stderr,
                }
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
