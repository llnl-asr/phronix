import subprocess

def register(mcp):
    @mcp.tool()
    def probe_run_pytest_subset(repo_path: str, test_targets: str, k_filter: str = "", extra_args: str = "") -> str:
        """Run pytest on given test file/dir paths inside a repo checkout.

        repo_path: absolute path to the repo checkout (cwd for the run).
        test_targets: space-separated test file/dir paths, relative to repo_path.
        k_filter: optional value for pytest's -k expression.
        extra_args: optional extra space-separated pytest args.

        Returns JSON: {status, returncode, summary_line, tail}.
        """
        import json
        cmd = ["python", "-m", "pytest"] + test_targets.split()
        if k_filter:
            cmd += ["-k", k_filter]
        if extra_args:
            cmd += extra_args.split()
        proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=600)
        out = proc.stdout + "\n" + proc.stderr
        lines = [l for l in out.splitlines() if l.strip()]
        summary_line = ""
        for l in reversed(lines):
            if "passed" in l or "failed" in l or "error" in l:
                summary_line = l
                break
        tail = "\n".join(lines[-40:])
        return json.dumps({
            "status": "ok",
            "returncode": proc.returncode,
            "summary_line": summary_line,
            "tail": tail,
        })
