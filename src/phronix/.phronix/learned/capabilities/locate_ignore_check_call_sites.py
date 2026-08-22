import subprocess


def register(mcp):
    @mcp.tool()
    def locate_ignore_check_call_sites(repo_path: str) -> str:
        """Grep pylint/lint/*.py under repo_path for _is_ignored_file and
        ignore-paths/ignore_paths references, returning matching
        file:line:text lines so the caller can see the helper's definition
        and every call site (expand_modules() and PyLinter._discover_files())
        in one shot.
        """
        proc = subprocess.run(
            [
                "grep",
                "-rn",
                "-E",
                "_is_ignored_file|ignore_paths|ignore-paths",
                f"{repo_path}/pylint/lint/",
            ],
            capture_output=True,
            text=True,
        )
        return proc.stdout or f"(no matches)\n{proc.stderr}"
