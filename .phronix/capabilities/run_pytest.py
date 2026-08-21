def register(mcp):
    @mcp.tool()
    def run_pytest():
        """Run pytest -q in the current working directory and return stdout, stderr, and returncode."""
        import subprocess
        result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
