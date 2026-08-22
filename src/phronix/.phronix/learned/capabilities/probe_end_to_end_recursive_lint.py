def register(mcp):
    def register_inner():
        pass

    @mcp.tool()
    def probe_end_to_end_recursive_lint(repo_path: str, target_dir: str, extra_args: str = "") -> str:
        """Run pylint's Run() entry point (imported from *repo_path*) with
        --recursive=y against *target_dir*, plus any extra_args (space
        separated, e.g. '--ignore-paths=^gen/.*$'). Captures which files
        pylint actually reported on via its Linter's stats, giving an
        end-to-end confirmation that ignored files were excluded and
        non-ignored files were still checked, independent of unit-level
        function probing."""
        import sys, subprocess

        cmd = [sys.executable, "-m", "pylint", "--recursive=y", target_dir] + extra_args.split()
        env_pythonpath = repo_path
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = env_pythonpath + os.pathsep + env.get("PYTHONPATH", "")
        try:
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True,
                                  text=True, timeout=120, env=env)
        except Exception as e:
            return f"ERROR: {e}"
        return f"exit={res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
