import os
import subprocess
import sys
import tempfile


def register(mcp):
    @mcp.tool()
    def verify_recursive_ignore_paths_fix(repo_root: str) -> str:
        """Build a small fixture tree (src/ok.py, src/gen/generated.py),
        run `python -m pylint --recursive=y --ignore-paths=^.*/gen/.*$ src`
        from repo_root's environment, and report whether generated.py was
        linted (bug present) or skipped (fix present). Returns a text
        summary.
        """
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = os.path.join(tmp, "src")
            gen_dir = os.path.join(src_dir, "gen")
            os.makedirs(gen_dir)
            with open(os.path.join(src_dir, "ok.py"), "w") as f:
                f.write("import os\n")
            with open(os.path.join(gen_dir, "generated.py"), "w") as f:
                f.write("import   os\nx=1\n")

            cmd = [
                sys.executable,
                "-m",
                "pylint",
                "--recursive=y",
                "--ignore-paths=^.*/gen/.*$",
                src_dir,
            ]
            proc = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            gen_linted = "generated.py" in output
            verdict = "BUG_PRESENT (generated.py was linted)" if gen_linted else "FIX_WORKS (generated.py was skipped)"
            return "%s\n---\n%s" % (verdict, output)
