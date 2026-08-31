import re


def register(mcp):
    @mcp.tool()
    def locate_python_def(file_path: str, def_name: str, context: int = 5) -> str:
        """Locate a 'def <def_name>' line in a Python file and return it with
        surrounding context lines. def_name may be a plain function/method name
        (e.g. '__init__') or a substring to match against the def line.
        Returns JSON: {status, matches: [{line_no, snippet}]}."""
        import json

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except OSError as e:
            return json.dumps({"status": "error", "detail": str(e)})

        pattern = re.compile(r"^\s*def\s+" + re.escape(def_name) + r"\s*\(")
        matches = []
        for i, line in enumerate(lines):
            if pattern.match(line):
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                snippet = "".join(lines[start:end])
                matches.append({"line_no": i + 1, "snippet": snippet})

        return json.dumps({"status": "ok", "matches": matches})
