def register(mcp):
    @mcp.tool()
    def add_dot_validation_blueprint_name():
        """Edit src/flask/blueprints.py to raise ValueError if '.' in blueprint name.
        This capability ensures Blueprint name cannot contain a dot.
        """
        import pathlib, re
        file_path = pathlib.Path('src/flask/blueprints.py')
        text = file_path.read_text()
        # Insert validation after the line setting self.name (or before usage)
        pattern = r"(self\.name\s*=\s*name)"
        repl = r"\1\n        if '.' in self.name:\n            raise ValueError('Blueprint name may not contain a dot.')"
        new_text = re.sub(pattern, repl, text)
        file_path.write_text(new_text)
        return 'dot validation added to name'
