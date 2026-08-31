def register(mcp):
    @mcp.tool()
    def probe_regex_path_separator_mismatch(sample_paths, patterns, path_sep=None):
        """Detect regex patterns that match a path under '/' but not under os.sep (or vice versa)."""
        import re, os
        sep = path_sep or os.sep
        results = []
        for pattern in patterns:
            compiled = re.compile(pattern)
            for p in sample_paths:
                native = p.replace('/', sep)
                posix = p.replace(sep, '/')
                m_native = bool(compiled.search(native))
                m_posix = bool(compiled.search(posix))
                if m_native != m_posix:
                    results.append({
                        "pattern": pattern,
                        "path": p,
                        "matches_native_sep": m_native,
                        "matches_posix_sep": m_posix,
                    })
        return {"mismatches": results, "count": len(results)}
