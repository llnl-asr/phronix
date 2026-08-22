import os
import shutil
import subprocess
import sys
import tempfile


def register(mcp):
    @mcp.tool()
    def check_ignore_paths_dot_recursive(repo_path: str) -> str:
        """Build a temp tree with an ignored subdirectory, run pylint's Run()
        with --recursive=y on '.' and an anchored ignore-paths regex against
        the given pylint checkout (repo_path), and report whether the file
        under the ignored subdirectory was correctly excluded.

        This reproduces the upstream PR #7080 regression scenario: os.walk('.')
        yields paths prefixed with './', which an anchored regex like
        '^ignored_subdirectory/.*' does not match unless the path is
        normalized before comparison in _is_ignored_file.

        Returns a short human-readable report: 'FIXED: ...' if the ignored
        file was correctly excluded, or 'BUG PRESENT: ...' if it leaked
        through, or 'ERROR: ...' on failure to run.
        """
        repo_path = os.path.abspath(repo_path)
        tmp = tempfile.mkdtemp(prefix="ignore_paths_dot_")
        try:
            sub = os.path.join(tmp, "ignored_subdirectory")
            os.makedirs(sub)
            with open(os.path.join(sub, "module.py"), "w") as f:
                f.write("import os\n")
            with open(os.path.join(tmp, "module.py"), "w") as f:
                f.write("x = 1\n")

            script = (
                "import sys\n"
                "from pylint.lint import Run\n"
                "from pylint.reporters.text import TextReporter\n"
                "import io\n"
                "buf = io.StringIO()\n"
                "try:\n"
                "    Run(['--recursive=y', '--ignore-paths=^ignored_subdirectory/.*', '.'],\n"
                "        reporter=TextReporter(buf), exit=False)\n"
                "except SystemExit:\n"
                "    pass\n"
                "sys.stdout.write(buf.getvalue())\n"
            )

            env = dict(os.environ)
            env["PYTHONPATH"] = repo_path

            proc = subprocess.run(
                [sys.executable, "-c", script],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            leaked = "ignored_subdirectory" in output
            if leaked:
                return f"BUG PRESENT: ignored_subdirectory/module.py was linted.\n{output}"
            return f"FIXED: ignored_subdirectory/module.py was correctly excluded.\n{output}"
        except Exception as exc:  # pragma: no cover
            return f"ERROR: {exc}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
