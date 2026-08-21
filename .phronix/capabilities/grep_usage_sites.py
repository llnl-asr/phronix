def register(mcp):
    import os
    import re

    @mcp.tool()
    def grep_usage_sites(root_dir: str, pattern: str, file_glob: str = "*.py") -> str:
        """Recursively search *root_dir* for files matching *file_glob*, returning every
        line matching regex *pattern* along with file:line. Use this to sanity-check
        whether adding a new validation/constraint would break any existing call sites
        (e.g. searching for Blueprint( calls with dots in the name argument).
        """
        import fnmatch

        rx = re.compile(pattern)
        hits = []
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for fname in filenames:
                if not fnmatch.fnmatch(fname, file_glob):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        for lineno, line in enumerate(f, start=1):
                            if rx.search(line):
                                hits.append(f"{fpath}:{lineno}: {line.rstrip()}")
                except OSError:
                    continue

        if not hits:
            return f"no matches for pattern {pattern!r} under {root_dir}"
        return "\n".join(hits)
