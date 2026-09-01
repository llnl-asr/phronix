def register(mcp):
    @mcp.tool()
    def append_changelog_entry(file_path: str, entry: str) -> str:
        """Append *entry* as a new bullet line under the first section heading
        of a CHANGES.rst-style file (the unreleased/top section).

        *entry* should be the bullet text without a leading '-'; it is
        inserted right after the section's underline, before the first
        existing bullet or blank gap.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        insert_at = None
        underline_idx = None
        for i, line in enumerate(lines):
            stripped = line.rstrip("\n")
            if stripped and set(stripped) <= {"-"} and i > 0 and lines[i - 1].strip():
                underline_idx = i
                break
        if underline_idx is None:
            return "NOT FOUND: no section heading/underline detected"

        insert_at = underline_idx + 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1

        bullet = f"-   {entry}\n"
        lines.insert(insert_at, bullet)

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return f"inserted at line {insert_at + 1}"
