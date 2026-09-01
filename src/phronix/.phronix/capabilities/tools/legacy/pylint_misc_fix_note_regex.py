def register(mcp):
    @mcp.tool()
    def fix_note_regex():
        """Update pylint/checkers/misc.py to match any characters after note tags.
        Replaces regex with '#\\s*({notes}|{self.config.notes_rgx})'"""
        import re, pathlib, sys
        file_path = pathlib.Path('pylint/checkers/misc.py')
        content = file_path.read_text()
        old = "regex_string = rf\"#\\s*({notes}|{self.config.notes_rgx})(?=\\b|$)\""
        new = "regex_string = rf\"#\\s*({notes}|{self.config.notes_rgx})\""
        updated = content.replace(old, new)
        file_path.write_text(updated)
        return 'updated'
