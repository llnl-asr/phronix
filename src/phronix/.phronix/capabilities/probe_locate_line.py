def register(mcp):
    @mcp.tool()
    def probe_locate_line(file: str, pattern: str) -> str:
        """Return matching lines with line numbers from the given file."""
        import subprocess
        result = subprocess.run(["grep", "-n", pattern, file], capture_output=True, text=True)
        return result.stdout
