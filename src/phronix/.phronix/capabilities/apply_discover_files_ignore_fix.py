import re
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def apply_discover_files_ignore_fix(repo_root: str) -> str:
        """Apply the combined fix to pylint/lint/pylinter.py::_discover_files.

        Two independent hunks, each idempotent:
        1. Filter each individually-yielded .py file through _is_ignored_file
           (not just the os.walk root), fixing --ignore-paths being silently
           ignored under --recursive=y.
        2. Make the skip_subtrees prefix check separator-bounded
           (root == s or root.startswith(s + os.sep)) instead of a bare
           startswith, so sibling dirs sharing a name prefix with an ignored
           dir aren't wrongly skipped.

        Returns a JSON-ish status string describing what was changed.
        """
        path = Path(repo_root) / "pylint" / "lint" / "pylinter.py"
        text = path.read_text()
        changes = []

        # Hunk 1: separator-bounded skip_subtrees check.
        old_subtree = "if any(root.startswith(s) for s in skip_subtrees):"
        new_subtree = (
            "if any(\n"
            "                    root == s or root.startswith(s + os.sep)\n"
            "                    for s in skip_subtrees\n"
            "                ):"
        )
        if old_subtree in text:
            text = text.replace(old_subtree, new_subtree)
            changes.append("subtree_boundary_fixed")
        elif "root == s or root.startswith(s + os.sep)" in text:
            changes.append("subtree_boundary_already_applied")
        else:
            changes.append("subtree_boundary_pattern_not_found")

        # Hunk 2: per-file ignore filtering in the non-package walk branch.
        # Look for the yield of individual files inside _discover_files and
        # ensure each is checked with _is_ignored_file before being yielded.
        if "_is_ignored_file(\n                            os.path.join(root, file)" in text:
            changes.append("file_filter_already_applied")
        else:
            # Match the else-branch that yields files directly under root.
            pattern = re.compile(
                r"(else:\n\s*yield from \(\n\s*os\.path\.join\(root, file\)\n\s*for file in files\n\s*if file\.endswith\(\"\.py\"\)\n\s*\))"
            )
            m = pattern.search(text)
            if m:
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
                changes.append("file_filter_applied")
            else:
                changes.append("file_filter_pattern_not_found_manual_edit_required")

        if "_is_ignored_file" not in text.split("\n")[0:60].__str__():
            pass  # import check left to caller; pylinter.py already imports expand_modules helpers in most versions

        path.write_text(text)
        return "{\"changes\": " + str(changes).replace("'", '"') + "}"
