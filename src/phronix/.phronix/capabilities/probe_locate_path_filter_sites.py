import subprocess


def register(mcp):
    @mcp.tool()
    def probe_locate_path_filter_sites(repo_root: str) -> str:
        """List every source line in *repo_root* referencing ignore_list_paths_re
        or the _is_ignored_file/_is_in_ignore_list_re helpers used to decide
        whether a discovered path is excluded by --ignore-paths.

        Returns newline-joined "path:lineno:text" matches from pylint/lint/.
        Useful for re-locating all filter sites when investigating recursive
        discovery / ignore-paths bugs without re-grepping by hand each time.
        """
        pattern = r"ignore_list_paths_re|_is_ignored_file|_is_in_ignore_list_re"
        try:
            out = subprocess.run(
                ["grep", "-rn", "-E", pattern, "pylint/lint"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            return f"error: {exc}"
        if out.returncode not in (0, 1):
            return f"grep failed: {out.stderr}"
        return out.stdout.strip() or "no matches"
