def register(mcp):
    @mcp.tool()
    def read_encoding_checker_regex() -> str:
        """Return the regex string built in EncodingChecker for note tags."""
        import pathlib, re
        file_path = pathlib.Path('pylint/checkers/misc.py')
        content = file_path.read_text()
        # Find the line where regex_string is defined
        for line in content.splitlines():
            if 'regex_string' in line:
                # Return the line stripped
                return line.strip()
        raise FileNotFoundError('regex_string not found')
