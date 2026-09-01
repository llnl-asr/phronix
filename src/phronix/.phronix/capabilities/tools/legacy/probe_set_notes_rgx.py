def register(mcp):
    @mcp.tool()
    def set_notes_rgx(repo_path: str, pattern: str):
        """Update pylintrc to set notes-rgx to given pattern."""
        import configparser, os
        rc_path = os.path.join(repo_path, 'pylintrc')
        cfg = configparser.ConfigParser()
        cfg.read(rc_path)
        if not cfg.has_section('MASTER'):
            cfg.add_section('MASTER')
        cfg.set('MASTER', 'notes-rgx', pattern)
        with open(rc_path, 'w') as f:
            cfg.write(f)
        return {'status':'ok'}