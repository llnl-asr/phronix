import re


def register(mcp):
    @mcp.tool()
    def normalize_root_leading_dotslash(pylinter_py_path: str) -> str:
        """Patch PyLinter._discover_files in the given pylint/lint/pylinter.py file.

        Applies two changes scoped to the os.walk loop in _discover_files only:
        1. Normalizes `root` via os.path.normpath right after os.walk yields it,
           so a leading './' (from running pylint on '.') does not break
           anchored ignore-paths regexes.
        2. Checks ignore status against both `root` and `root + os.sep`, so
           directory-anchored ignore-paths patterns (e.g. '^ignored_subdirectory/.*$')
           match the bare directory itself, not just files inside it.

        Does NOT touch pylint/lint/expand_modules.py's _is_ignored_file/_is_in_ignore_list_re
        helpers or any other call site -- doing so regresses
        tests/lint/unittest_expand_modules.py::test_expand_modules_with_ignore.

        Returns "ok: patched" or "ok: already patched" or an error string.
        """
        with open(pylinter_py_path, encoding="utf-8") as f:
            content = f.read()

        if "root = os.path.normpath(root)" in content:
            return "ok: already patched"

        old = (
            "                skip_subtrees: list[str] = []\n"
            "                for root, _, files in os.walk(something):\n"
            "                    if any(root.startswith(s) for s in skip_subtrees):\n"
            "                        # Skip subtree of already discovered package.\n"
            "                        continue\n"
            "\n"
            "                    if _is_ignored_file(\n"
            "                        root,\n"
            "                        self.config.ignore,\n"
            "                        self.config.ignore_patterns,\n"
            "                        self.config.ignore_paths,\n"
            "                    ):\n"
        )
        new = (
            "                skip_subtrees: list[str] = []\n"
            "                for root, _, files in os.walk(something):\n"
            "                    root = os.path.normpath(root)\n"
            "                    if any(root.startswith(s) for s in skip_subtrees):\n"
            "                        # Skip subtree of already discovered package.\n"
            "                        continue\n"
            "\n"
            "                    if _is_ignored_file(\n"
            "                        root,\n"
            "                        self.config.ignore,\n"
            "                        self.config.ignore_patterns,\n"
            "                        self.config.ignore_paths,\n"
            "                    ) or _is_ignored_file(\n"
            "                        root + os.sep,\n"
            "                        self.config.ignore,\n"
            "                        self.config.ignore_patterns,\n"
            "                        self.config.ignore_paths,\n"
            "                    ):\n"
        )

        if old not in content:
            return "error: expected _discover_files shape not found; file may already differ from base commit"

        content = content.replace(old, new)
        with open(pylinter_py_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "ok: patched"
