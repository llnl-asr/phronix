def register(mcp):
    @mcp.tool()
    def remove_filterwarnings_error(path: str = "setup.cfg") -> str:
        """Replace filterwarnings block in setup.cfg to ignore DeprecationWarning.
        Returns a short message indicating success.
        """
        from pathlib import Path
        import re
        cfg_path = Path(path)
        if not cfg_path.is_file():
            raise FileNotFoundError(f"{path} not found")
        content = cfg_path.read_text()
        # Replace the filterwarnings block (including following indented lines) with the desired block.
        pattern = r"filterwarnings\s*=\s*\n(?:\s+.*\n)*"
        replacement = "filterwarnings =\n    ignore::DeprecationWarning\n    error\n"
        new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
        cfg_path.write_text(new_content)
        return f"Updated {path}, replacements made: {count}"