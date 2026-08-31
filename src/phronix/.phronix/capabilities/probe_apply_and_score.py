import subprocess

def register(mcp):
    @mcp.tool()
    def probe_apply_and_score(repo_path: str, file_path: str, old_text: str, new_text: str, test_path: str, k_filter: str = "") -> str:
        """Apply an exact string replacement (old_text -> new_text, must be
        unique) to file_path, then run `pytest <test_path> -k <k_filter> -q`
        inside repo_path. Returns whether the patch applied and the test
        return code, so a candidate change can be scored end-to-end in one
        call. Does not revert the patch — caller is responsible for git
        checkout/stash if the candidate should be discarded."""
        with open(file_path, "r") as f:
            content = f.read()
        count = content.count(old_text)
        if count == 0:
            return "error: old_text not found"
        if count > 1:
            return f"error: old_text not unique ({count} occurrences)"
        content = content.replace(old_text, new_text, 1)
        with open(file_path, "w") as f:
            f.write(content)

        cmd = ["python", "-m", "pytest", test_path, "-q"]
        if k_filter:
            cmd += ["-k", k_filter]
        try:
            out = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=600)
        except Exception as e:
            return f"patched but test run errored: {e}"
        tail = "\n".join((out.stdout + out.stderr).splitlines()[-40:])
        return f"patch_applied=true\ntest_returncode={out.returncode}\n{tail}"
