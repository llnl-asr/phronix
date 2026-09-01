import os
import subprocess
import sys

def register(mcp):
    @mcp.tool()
    def reproduce_recursive_ignore_leak(repo_path: str, base_dir: str, ignore_paths_pattern: str, target: str) -> str:
        """Create base_dir/subdir/__init__.py and base_dir/other.py, then run
        `python -m pylint --recursive=y --ignore-paths=<ignore_paths_pattern> <target>`
        with repo_path's pylint on PYTHONPATH, from within base_dir. Returns
        combined stdout/stderr so the caller can check whether files under the
        ignored pattern were incorrectly linted (leaked)."""
        subdir = os.path.join(base_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        with open(os.path.join(subdir, "__init__.py"), "w") as f:
            f.write("# fixture package\n")
        with open(os.path.join(base_dir, "other.py"), "w") as f:
            f.write("# fixture module\n")

        env = dict(**{"PYTHONPATH": repo_path})
        try:
            out = subprocess.run(
                [sys.executable, "-m", "pylint", "--recursive=y",
                 f"--ignore-paths={ignore_paths_pattern}", target],
                cwd=base_dir, capture_output=True, text=True, timeout=60, env=env,
            )
        except Exception as e:
            return f"error: {e}"
        return f"returncode={out.returncode}\n{out.stdout}\n{out.stderr}"
