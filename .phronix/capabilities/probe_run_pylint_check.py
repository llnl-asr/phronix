import subprocess

def register(mcp):
    @mcp.tool()
    def probe_run_pylint_check(repo_path: str, target_path: str, pylint_args: str = "", file_content: str = "") -> str:
        """Run pylint against *target_path* inside *repo_path* using `python -m pylint`.

        If *file_content* is non-empty, it is written to *target_path* first
        (creating/overwriting it), which is handy for building a small repro
        snippet before checking which messages pylint emits. *pylint_args* is
        a space-separated string of extra CLI args, e.g.
        '--disable=all --enable=fixme --notes=YES,???'. Returns the combined
        stdout/stderr from pylint (including message codes like W0511), which
        can be checked for expected messages/lines.
        """
        if file_content:
            try:
                with open(f"{repo_path.rstrip('/')}/{target_path}", "w", encoding="utf-8") as f:
                    f.write(file_content)
            except OSError as e:
                return f"error writing target: {e}"

        cmd = ["python", "-m", "pylint", target_path]
        if pylint_args:
            cmd += pylint_args.split()
        try:
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=60)
        except Exception as e:
            return f"ERROR: {e}"
        return f"exit={res.returncode}\n{res.stdout}\n{res.stderr}"
