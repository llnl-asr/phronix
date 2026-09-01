import subprocess

def register(mcp):
    @mcp.tool()
    def locate_code_symbol(repo_root: str, symbol: str, context: int = 15) -> str:
        """Grep *repo_root* for *symbol* and return each match with *context* lines
        of surrounding code, to locate the right place to make an edit.
        """
        try:
            out = subprocess.run(
                ["grep", "-rn", "-C", str(context), symbol, repo_root,
                 "--include=*.py"],
                capture_output=True, text=True, timeout=30,
            )
            result = out.stdout.strip()
            if not result:
                return f"no matches for {symbol!r} under {repo_root}"
            if len(result) > 20000:
                result = result[:20000] + "\n...[truncated]"
            return result
        except Exception as e:
            return f"error: {e}"
