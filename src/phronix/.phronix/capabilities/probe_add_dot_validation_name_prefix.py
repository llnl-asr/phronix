def register(mcp):
    @mcp.tool()
    def add_dot_validation_name_prefix():
        """Edit src/flask/blueprints.py to raise ValueError if '.' in name_prefix.
        This capability ensures Blueprint name_prefix cannot contain a dot, mirroring endpoint validation.
        """
        import pathlib, re
        file_path = pathlib.Path('src/flask/blueprints.py')
        text = file_path.read_text()
        # Find the line assigning self.name_prefix and insert validation after it.
        pattern = r"(self\.name_prefix\s*=\s*name_prefix)"
        repl = r"\1\n        if '.' in self.name_prefix:\n            raise ValueError('Blueprint name_prefix may not contain a dot.')"
        new_text = re.sub(pattern, repl, text)
        file_path.write_text(new_text)
        return 'dot validation added'
