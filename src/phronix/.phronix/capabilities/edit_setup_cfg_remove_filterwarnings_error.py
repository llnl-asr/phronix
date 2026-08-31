def register(mcp):
    @mcp.tool()
    def edit_setup_cfg_remove_filterwarnings_error(path: str) -> str:
        """Remove filterwarnings error lines from the setup.cfg file at *path*.
        Returns a message indicating what was changed.
        """
        import pathlib
        cfg_path = pathlib.Path(path)
        if not cfg_path.is_file():
            return f"setup.cfg not found at {path}"
        lines = cfg_path.read_text().splitlines()
        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            stripped = line.strip()
            if stripped.startswith('filterwarnings'):
                # Next line is likely the indented "error" line; skip it as well
                # Ensure we also skip the following indented line if present
                # Look ahead to see if next line is indented and not empty
                if i + 1 < len(lines) and lines[i+1].startswith('    '):
                    skip_next = True
                continue
            new_lines.append(line)
        cfg_path.write_text('\n'.join(new_lines) + '\n')
        return "Removed filterwarnings error from setup.cfg"
