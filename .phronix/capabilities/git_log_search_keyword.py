import subprocess

def register(mcp):
    @mcp.tool()
    def git_log_search_keyword(repo_path: str, keyword: str, search_diffs: bool = False, max_results: int = 20) -> str:
        """Search git commit history in *repo_path* for *keyword*.

        Searches commit messages via `git log --grep`. If *search_diffs* is
        True, also searches commit content/diffs via `git log -S<keyword>`
        (pickaxe search) and appends those results. Useful for locating the
        upstream commit that fixed a given issue number or topic before
        reimplementing it. Returns up to *max_results* one-line commit
        summaries per search mode.
        """
        out = []
        try:
            res = subprocess.run(
                ["git", "log", f"--grep={keyword}", "-i", "--oneline", f"-n{max_results}"],
                cwd=repo_path, capture_output=True, text=True, timeout=30,
            )
            out.append("grep(message):\n" + (res.stdout.strip() or "(no matches)"))
        except Exception as e:
            out.append(f"grep(message) error: {e}")

        if search_diffs:
            try:
                res = subprocess.run(
                    ["git", "log", f"-S{keyword}", "--oneline", f"-n{max_results}"],
                    cwd=repo_path, capture_output=True, text=True, timeout=30,
                )
                out.append("pickaxe(diff):\n" + (res.stdout.strip() or "(no matches)"))
            except Exception as e:
                out.append(f"pickaxe(diff) error: {e}")

        return "\n\n".join(out)
