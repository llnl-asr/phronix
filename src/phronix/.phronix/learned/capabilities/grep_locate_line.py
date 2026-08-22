import re

def register(mcp):
    @mcp.tool()
    def grep_locate_line(path: str, pattern: str, context: int = 0) -> str:
        """Return line numbers (1-indexed) and text of lines in *path* matching regex *pattern*.

        Optionally include *context* lines before/after each match. Useful for
        locating an insertion point such as `self.name = name` inside a class
        __init__ before editing.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            return f"error: {e}"

        rx = re.compile(pattern)
        matches = []
        for i, line in enumerate(lines):
            if rx.search(line):
                lo = max(0, i - context)
                hi = min(len(lines), i + context + 1)
                snippet = "".join(
                    f"{j+1}: {lines[j]}" for j in range(lo, hi)
                )
                matches.append({"line": i + 1, "text": line.rstrip("\n"), "context": snippet})

        if not matches:
            return "no matches"

        out = []
        for m in matches:
            out.append(f"L{m['line']}: {m['text']}")
            if context:
                out.append(m["context"])
        return "\n".join(out)
