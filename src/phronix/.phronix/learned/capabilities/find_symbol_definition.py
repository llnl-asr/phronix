def register(mcp):
    import re

    @mcp.tool()
    def find_symbol_definition(file_path: str, pattern: str, context: int = 3) -> str:
        """Find lines matching a regex *pattern* in *file_path*, returning line numbers
        with surrounding context lines. Useful for locating a class/def/assignment to
        determine where to insert new code (e.g. finding `self.name = name` inside
        `class Blueprint.__init__`).
        """
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except OSError as e:
            return f"error: {e}"

        rx = re.compile(pattern)
        hits = []
        for i, line in enumerate(lines):
            if rx.search(line):
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                snippet = "".join(
                    f"{n + 1}: {lines[n]}" for n in range(start, end)
                )
                hits.append(f"--- match at line {i + 1} ---\n{snippet}")

        if not hits:
            return f"no matches for pattern {pattern!r} in {file_path}"
        return "\n".join(hits)
