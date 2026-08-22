import subprocess

def register(mcp):
    @mcp.tool()
    def locate_discover_files_ignore_check(repo_root: str) -> str:
        """Grep the pylint lint package for _discover_files and _is_ignored_file
        definitions and call sites, to locate the recursive discovery loop and
        its existing directory-level ignore check."""
        patterns = ["_discover_files", "_is_ignored_file"]
        out = []
        for pat in patterns:
            try:
                r = subprocess.run(
                    ["grep", "-rn", pat, f"{repo_root}/pylint/lint"],
                    capture_output=True, text=True, timeout=30,
                )
                out.append(f"# {pat}\n{r.stdout or '(no matches)'}")
            except Exception as e:
                out.append(f"# {pat}\nERROR: {e}")
        return "\n\n".join(out)
