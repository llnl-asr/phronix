import subprocess

def register(mcp):
    @mcp.tool()
    def grep_locate_pattern_in_repo(repo_path: str, pattern: str, glob: str = "*.py", context: int = 3) -> str:
        """Grep recursively under repo_path for pattern (regex, extended grep -E)
        restricted to files matching glob, with `context` lines of context.
        Generic code-location probe reusable across tasks."""
        try:
            out = subprocess.run(
                ["grep", "-rn", "-E", f"-C{context}", "--include", glob, pattern, repo_path],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            return f"error: {e}"
        if out.returncode not in (0, 1):
            return f"grep failed: {out.stderr}"
        return out.stdout or "no match found"
