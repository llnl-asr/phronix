def register(mcp):
    @mcp.tool()
    def apply_discover_files_per_file_ignore_patch(pylinter_py_path: str) -> str:
        """Edit pylint/lint/pylinter.py so the non-package else branch of
        _discover_files also filters each individual .py file through
        _is_ignored_file (ignore/ignore_patterns/ignore_paths), leaving the
        existing directory-level check untouched. Returns a status message;
        idempotent (no-op if already patched)."""
        with open(pylinter_py_path, "r", encoding="utf-8") as f:
            content = f.read()

        old = (
            "                yield from (\n"
            "                    os.path.join(root, file)\n"
            "                    for file in files\n"
            "                    if file.endswith(\".py\")\n"
            "                )"
        )
        new = (
            "                yield from (\n"
            "                    os.path.join(root, file)\n"
            "                    for file in files\n"
            "                    if file.endswith(\".py\")\n"
            "                    and not _is_ignored_file(\n"
            "                        os.path.join(root, file),\n"
            "                        self.config.ignore,\n"
            "                        self.config.ignore_patterns,\n"
            "                        self.config.ignore_paths,\n"
            "                    )\n"
            "                )"
        )

        if new in content:
            return "already patched"
        if old not in content:
            return "PATTERN_NOT_FOUND: manual inspection required"

        content = content.replace(old, new)

        if "from pylint.lint.expand_modules import" in content:
            if "_is_ignored_file" not in content.split("\n\n", 1)[0]:
                pass

        with open(pylinter_py_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "patched"
