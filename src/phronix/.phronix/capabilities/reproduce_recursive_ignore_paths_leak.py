import os
import subprocess
import sys


def register(mcp):
    @mcp.tool()
    def reproduce_recursive_ignore_paths_leak(repo_root: str, ignore_paths_regex: str = r"^tests/regrtest_data/directory/ignored_subdirectory/.*$") -> str:
        """Run PyLinter._discover_files under --recursive=y with the given --ignore-paths
        regex against tests/regrtest_data/directory in *repo_root*, and report whether any
        files under ignored_subdirectory still leak through (the pylint #7080 bug).

        Use a regex that requires trailing content after the directory name (like the
        issue's ^src/gen/.*$) — regexes matching the bare directory path (e.g.
        '.*directory/ignored.*') do not exercise the bug and will falsely look fixed.
        """
        script = (
            "import os\n"
            "from pylint.lint import Run\n"
            "REGRTEST_DATA_DIR = 'tests/regrtest_data'\n"
            "run = Run(['--recursive', 'y', '--ignore-paths', %r, os.path.join(REGRTEST_DATA_DIR, 'directory')], exit=False)\n"
            "files = list(run.linter._discover_files([os.path.join(REGRTEST_DATA_DIR, 'directory')]))\n"
            "for f in files:\n"
            "    print(f)\n"
        ) % ignore_paths_regex

        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return "ERROR running reproduction:\n" + proc.stderr

        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        leaked = [f for f in files if "ignored_subdirectory" in f]
        if leaked:
            return "BUG REPRODUCED: ignored files leaked through discovery:\n" + "\n".join(leaked)
        return "NO LEAK: ignore-paths correctly excluded ignored_subdirectory.\nDiscovered files:\n" + "\n".join(files)
