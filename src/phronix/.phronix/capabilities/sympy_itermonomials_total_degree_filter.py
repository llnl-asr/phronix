def register(mcp):
    @mcp.tool()
    def replace_max_with_sum(file_path: str):
        """Replace max(powers.values()) with sum(powers.values()) in the given file.
        Returns a dict with status and number of replacements.
        """
        import pathlib, re
        path = pathlib.Path(file_path)
        text = path.read_text()
        new_text, count = re.subn(r"max\(powers\.values\(\)\)", "sum(powers.values())", text)
        if count:
            path.write_text(new_text)
        return {"status": "ok", "replacements": count}
