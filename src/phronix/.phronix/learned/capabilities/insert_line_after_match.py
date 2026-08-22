import re

def register(mcp):
    @mcp.tool()
    def insert_line_after_match(path: str, pattern: str, new_text: str, match_index: int = 0) -> str:
        """Insert *new_text* immediately after the line in *path* matching regex *pattern*.

        *new_text* may contain multiple lines (joined with \\n); each inserted line
        is auto-indented to match the indentation of the matched line. *match_index*
        selects which match to use when the pattern occurs more than once (0-based,
        default first match). Returns a diff-like confirmation or an error string.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            return f"error: {e}"

        rx = re.compile(pattern)
        match_positions = [i for i, line in enumerate(lines) if rx.search(line)]
        if not match_positions:
            return "error: no matches found"
        if match_index >= len(match_positions):
            return f"error: match_index {match_index} out of range ({len(match_positions)} matches)"

        pos = match_positions[match_index]
        matched_line = lines[pos]
        indent = matched_line[: len(matched_line) - len(matched_line.lstrip())]

        new_lines = [indent + segment + "\n" for segment in new_text.split("\n")]
        updated = lines[: pos + 1] + new_lines + lines[pos + 1 :]

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(updated)

        return f"inserted {len(new_lines)} line(s) after line {pos + 1} in {path}"
