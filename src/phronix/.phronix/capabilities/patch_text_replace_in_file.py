def register(mcp):
    @mcp.tool()
    def patch_text_replace_in_file(file_path: str, old_text: str, new_text: str) -> str:
        """Replace the first occurrence of old_text with new_text in file_path.
        Errors if old_text is not found or appears more than once, so callers
        can trust the patch landed at the intended, unambiguous location."""
        with open(file_path, "r") as f:
            content = f.read()
        count = content.count(old_text)
        if count == 0:
            return "error: old_text not found in file"
        if count > 1:
            return f"error: old_text is not unique ({count} occurrences); provide more context"
        content = content.replace(old_text, new_text, 1)
        with open(file_path, "w") as f:
            f.write(content)
        return f"ok: replaced 1 occurrence in {file_path}"
