import re

def register(mcp):
    @mcp.tool()
    def regex_replace_in_file(path: str, pattern: str, replacement: str, count: int = 1, flags_dotall: bool = False) -> str:
        """Replace text in *path* matching regex *pattern* with *replacement*.

        *pattern* and *replacement* follow Python re syntax (use \\1, \\2 for
        backreferences). *count* limits the number of replacements (0 = all).
        Set *flags_dotall* True to let '.' match newlines, useful for
        multi-line constructs. Returns a confirmation with the number of
        replacements made, or an error string if the pattern is not found.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            return f"error: {e}"

        flags = re.DOTALL if flags_dotall else 0
        rx = re.compile(pattern, flags)
        new_text, n = rx.subn(replacement, text, count=count)
        if n == 0:
            return "error: pattern not found"

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)

        return f"replaced {n} occurrence(s) in {path}"
