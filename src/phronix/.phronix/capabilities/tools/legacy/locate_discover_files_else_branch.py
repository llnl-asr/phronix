import subprocess

def register(mcp):
    @mcp.tool()
    def locate_discover_files_else_branch(repo_path: str) -> str:
        """Grep repo_path/pylint/lint/pylinter.py for the _discover_files method
        and its else-branch generator that yields loose .py files without
        calling _is_ignored_file on them. Returns matching lines with numbers."""
        target = f"{repo_path}/pylint/lint/pylinter.py"
        try:
            out = subprocess.run(
                ["grep", "-n", "-A", "3", "-B", "20", "yield from", target],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            return f"error: {e}"
        if out.returncode not in (0, 1):
            return f"grep failed: {out.stderr}"
        return out.stdout or "no match found"
