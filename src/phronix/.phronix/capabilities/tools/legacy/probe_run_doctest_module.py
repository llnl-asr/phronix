def register(mcp):
    import subprocess

    @mcp.tool()
    def probe_run_doctest_module(repo_path: str, module_path: str) -> str:
        """Run `python -m doctest <module_path> -v` inside *repo_path* and
        return a pass/fail summary plus any failure details. module_path is
        a path relative to repo_path, e.g. 'sympy/polys/monomials.py'.
        Use this to verify a fixed function's docstring examples (>>> ...)
        still produce the documented output after an edit."""
        cmd = ["python", "-m", "doctest", module_path]
        try:
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True,
                                  text=True, timeout=120)
        except Exception as e:
            return f"ERROR: {e}"
        out = (res.stdout + res.stderr).strip()
        if res.returncode == 0 and not out:
            return "exit=0 all doctest examples passed"
        tail = "\n".join(out.splitlines()[-60:])
        return f"exit={res.returncode}\n{tail}"
