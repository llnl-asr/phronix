import re
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def apply_discover_files_file_filter_only(repo_root: str) -> str:
        """Apply only the per-file ignore-paths filter to _discover_files.

        Narrower fallback than apply_discover_files_ignore_fix: leaves the
        skip_subtrees prefix check untouched, only filters each yielded .py
        file through _is_ignored_file so --ignore-paths is honored under
        --recursive=y.
        """
        path = Path(repo_root) / "pylint" / "lint" / "pylinter.py"
        text = path.read_text()

        if "_is_ignored_file(\n                            os.path.join(root, file)" in text:
            return "{\"changes\": [\"file_filter_already_applied\"]}"

        pattern = re.compile(
            r"(else:\n\s*yield from \(\n\s*os\.path\.join\(root, file\)\n\s*for file in files\n\s*if file\.endswith\(\"\.py\"\)\n\s*\))"
        )
        m = pattern.search(text)
        if not m:
            return "{\"changes\": [\"file_filter_pattern_not_found_manual_edit_required\"]}"

        replacement = (
            "else:\n"
            "                    yield from (\n"
            "                        os.path.join(root, file)\n"
            "                        for file in files\n"
            "                        if file.endswith(\".py\")\n"
            "                        and not _is_ignored_file(\n"
            "                            os.path.join(root, file),\n"
            "                            self.config.ignore,\n"
            "                            self.config.ignore_patterns,\n"
            "                            self.config.ignore_paths,\n"
            "                        )\n"
            "                    )"
        )
        text = text[: m.start()] + replacement + text[m.end() :]
        path.write_text(text)
        return "{\"changes\": [\"file_filter_applied\"]}"
