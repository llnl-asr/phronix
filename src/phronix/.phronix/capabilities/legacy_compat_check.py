def register(mcp):
    @mcp.tool()
    def check_deprecated_flask_usage(path: str) -> str:
        """Scans the given file for deprecated Flask API usage such as `flask.send_file` signatures that changed in Flask 2.0.
        Returns a JSON string with `found: bool` and `details: list` of line numbers.
        """
        import re, json, pathlib
        file_path = pathlib.Path(path)
        if not file_path.is_file():
            return json.dumps({"found": False, "error": "File not found"})
        pattern = re.compile(r"send_file\([^,]+,\s*as_attachment=", re.IGNORECASE)
        findings = []
        for i, line in enumerate(file_path.read_text().splitlines(), start=1):
            if pattern.search(line):
                findings.append({"line": i, "code": line.strip()})
        return json.dumps({"found": bool(findings), "details": findings})
