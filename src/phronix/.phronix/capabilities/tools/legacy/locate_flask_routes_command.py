def register(mcp):
    import subprocess

    @mcp.tool()
    def locate_flask_routes_command(repo_path: str) -> str:
        """Grep repo_path/src/flask/cli.py for the `routes_command` function
        definition and the surrounding table-building code (headers, widths,
        row format string, echo loop). Returns matching lines with numbers so
        the caller can jump straight to the code that needs editing when
        adding/changing columns in `flask routes` output."""
        cmd = [
            "grep", "-n",
            "-e", "def routes_command",
            "-e", "headers",
            "-e", "widths",
            "-e", "row =",
            "-e", "iter_rules",
            f"{repo_path}/src/flask/cli.py",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.stdout or res.stderr or "no matches"
