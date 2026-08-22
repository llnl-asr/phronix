def register(mcp):
    import subprocess

    @mcp.tool()
    def locate_ignore_matching_function(repo_path: str, symbol: str = "_is_ignored_file") -> str:
        """Grep *repo_path* for *symbol* (default '_is_ignored_file') and its
        common companions ('ignore_list_paths_re', '_is_in_ignore_list_re'),
        returning file:line matches. Used to find where ignore-paths/
        ignore-patterns regex matching is defined and called from, so a fix
        can be scoped to the exact function without a broad manual search."""
        terms = [symbol, "ignore_list_paths_re", "_is_in_ignore_list_re"]
        out = []
        for term in terms:
            try:
                res = subprocess.run(
                    ["grep", "-rn", term, repo_path,
                     "--include=*.py"],
                    capture_output=True, text=True, timeout=30,
                )
                out.append(f"## {term}\n{res.stdout.strip()}")
            except Exception as e:
                out.append(f"## {term}\nERROR: {e}")
        return "\n\n".join(out)
