import json


def register(mcp):
    @mcp.tool()
    def probe_read_file_region(file_path: str, start_line: int, end_line: int) -> str:
        """Read lines start_line..end_line (1-indexed, inclusive) from file_path
        and return JSON {status, ok, lines} where lines is a list of
        "N: content" strings. Use this to inspect a specific branch or function
        in a source file before deciding how to patch it."""
        try:
            with open(file_path, "r") as f:
                all_lines = f.readlines()
        except Exception as e:
            return json.dumps({"status": "error", "ok": False, "error": str(e)})
        start = max(1, start_line)
        end = min(len(all_lines), end_line)
        out = [f"{i}: {all_lines[i - 1].rstrip(chr(10))}" for i in range(start, end + 1)]
        return json.dumps({"status": "ok", "ok": True, "lines": out})
