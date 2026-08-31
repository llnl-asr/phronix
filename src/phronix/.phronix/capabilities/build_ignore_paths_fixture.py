import os
import json


def register(mcp):
    @mcp.tool()
    def build_ignore_paths_fixture(
        base_dir: str,
        ignored_subdir: str = "src/gen",
        ignore_regex: str = "",
        clean_file_rel: str = "src/region_selection.py",
        ignored_file_rel: str = "",
    ) -> str:
        """Create a throwaway fixture tree under *base_dir* mirroring the
        pylint ignore-paths/--recursive bug shape: a clean source file plus a
        nested directory (default src/gen) that should be excluded by an
        ignore-paths regex, with a pyproject.toml declaring
        [tool.pylint.MASTER] ignore-paths = ["<ignore_regex>"].

        ignore_regex defaults to "^<ignored_subdir>/.*$" if not given.
        ignored_file_rel defaults to "<ignored_subdir>/about.py" if not given.

        Both the clean and ignored files contain a lint violation (unused
        import) so a correct run reports only the clean file's violation.

        Returns JSON: {"status", "base_dir", "clean_file", "ignored_file",
        "pyproject_toml", "ignore_regex"}.
        """
        if not ignore_regex:
            ignore_regex = f"^{ignored_subdir}/.*$"
        if not ignored_file_rel:
            ignored_file_rel = os.path.join(ignored_subdir, "about.py")

        clean_file = os.path.join(base_dir, clean_file_rel)
        ignored_file = os.path.join(base_dir, ignored_file_rel)

        os.makedirs(os.path.dirname(clean_file), exist_ok=True)
        os.makedirs(os.path.dirname(ignored_file), exist_ok=True)

        violation = "import os\n\n\ndef f():\n    pass\n"
        with open(clean_file, "w") as fh:
            fh.write(violation)
        with open(ignored_file, "w") as fh:
            fh.write(violation)

        pyproject = os.path.join(base_dir, "pyproject.toml")
        with open(pyproject, "w") as fh:
            fh.write(
                "[tool.pylint.MASTER]\n"
                f'ignore-paths = ["{ignore_regex}"]\n'
            )

        return json.dumps({
            "status": "ok",
            "base_dir": base_dir,
            "clean_file": clean_file,
            "ignored_file": ignored_file,
            "pyproject_toml": pyproject,
            "ignore_regex": ignore_regex,
        })
