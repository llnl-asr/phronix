import os
import re


def register(mcp):
    @mcp.tool()
    def probe_find_changelog_fragment_dir(repo_root: str) -> str:
        """Find the doc/whatsnew fragment directory for the next unreleased
        pylint version (towncrier-style layout: doc/whatsnew/<major>/<minor>/).

        Returns the deepest numeric-named directory under doc/whatsnew that
        contains no further numeric subdirectories, or an explanatory string
        if the repo does not use this layout.
        """
        base = os.path.join(repo_root, "doc", "whatsnew")
        if not os.path.isdir(base):
            return f"no doc/whatsnew directory under {repo_root}"

        def numeric_subdirs(path):
            try:
                return sorted(
                    d for d in os.listdir(path)
                    if os.path.isdir(os.path.join(path, d)) and re.fullmatch(r"\d+", d)
                )
            except OSError:
                return []

        current = base
        while True:
            subs = numeric_subdirs(current)
            if not subs:
                break
            current = os.path.join(current, subs[-1])

        if current == base:
            return f"no numeric version subdirectories found under {base}"
        return current
