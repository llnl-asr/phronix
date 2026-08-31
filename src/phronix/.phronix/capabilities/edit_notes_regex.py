def register(mcp):
    @mcp.tool()
    def edit_notes_regex_tool():
        """Edit pylint's notes regex to include lookahead for whitespace, end or colon.
        This ensures punctuation-only note tags are recognized by --notes.
        """
        import pathlib, sys
        path = pathlib.Path('pylint/checkers/misc.py')
        old = r"regex_string = rf\"#\\s*({notes}|{self.config.notes_rgx})\\b\""
        new = r"regex_string = rf\"#\\s*({notes}|{self.config.notes_rgx})(?=\\s|$|:)\\b\""
        try:
            text = path.read_text()
        except Exception as e:
            return f"Failed to read file: {e}"
        if old not in text:
            return "Pattern not found; maybe already edited"
        updated = text.replace(old, new)
        try:
            path.write_text(updated)
        except Exception as e:
            return f"Failed to write file: {e}"
        return "Regex updated successfully"
