import subprocess
import sys
import tempfile
import os
import shutil
import json


def register(mcp):
    @mcp.tool()
    def probe_recursive_ignore_paths(
        files: str,
        ignore: str = "",
        ignore_patterns: str = "",
        ignore_paths: str = "",
        recursive: str = "y",
    ) -> str:
        """Create a temp directory tree from *files* (JSON list of relative paths,
        each written with a trivial valid python body), then run
        `python -m pylint --recursive=<recursive> --ignore=<ignore>
        --ignore-patterns=<ignore_patterns> --ignore-paths=<ignore_paths> <root>`
        inside a fresh tempdir. Returns JSON {returncode, stdout, stderr,
        linted_files: [relative paths pylint actually reported on]}.

        *files* entries ending in '/' are treated as directories to create
        (with an empty dir, no file); otherwise a .py file is written.
        ignore / ignore_patterns / ignore_paths are comma-separated raw
        values passed straight to the corresponding pylint options.
        """
        file_list = json.loads(files)
        workdir = tempfile.mkdtemp(prefix="pylint_ignorepaths_")
        root = os.path.join(workdir, "pkg")
        os.makedirs(root, exist_ok=True)
        try:
            for rel in file_list:
                full = os.path.join(root, rel)
                if rel.endswith("/"):
                    os.makedirs(full, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w") as f:
                    f.write("x = 1\n")

            cmd = [sys.executable, "-m", "pylint", f"--recursive={recursive}"]
            if ignore:
                cmd.append(f"--ignore={ignore}")
            if ignore_patterns:
                cmd.append(f"--ignore-patterns={ignore_patterns}")
            if ignore_paths:
                cmd.append(f"--ignore-paths={ignore_paths}")
            cmd.append(root)

            proc = subprocess.run(
                cmd, cwd=workdir, capture_output=True, text=True, timeout=120
            )
            linted = sorted(
                set(
                    line.split("Module ", 1)[1].strip()
                    for line in proc.stdout.splitlines()
                    if line.startswith("*") and "Module " in line
                )
            )
            return json.dumps(
                {
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "linted_files": linted,
                }
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
