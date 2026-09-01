def register(mcp):
    @mcp.tool()
    def add_blueprint_name_dot_check():
        """Add validation to Blueprint.__init__ to raise error if name contains a dot."""
        import pathlib
        path = pathlib.Path('src/flask/blueprints.py')
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            if 'self.name = name' in line:
                indent = line[:line.find('self.name')]
                check_line1 = f"{indent}if '.' in name:"
                check_line2 = f"{indent}    raise ValueError(\"'name' may not contain a dot '.' character.\")"
                lines.insert(i+1, check_line1)
                lines.insert(i+2, check_line2)
                break
        path.write_text('\n'.join(lines) + '\n')