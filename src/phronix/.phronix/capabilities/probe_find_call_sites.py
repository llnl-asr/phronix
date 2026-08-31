import json
import subprocess


def register(mcp):
    @mcp.tool()
    def probe_find_call_sites(repo_root: str, symbol: str, path_glob: str = "**/*.py", context: int = 1) -> str:
        """Grep *repo_root* (restricted to files matching *path_glob*) for
        occurrences of *symbol* (e.g. a function/method name like
        '_collect_factor_and_dimension(') and return matching lines with
        *context* lines of surrounding context. Returns JSON
        {status, ok, matches: [str]}. Use this before changing a function's
        return arity/shape to see how every caller unpacks its result.
        """
        proc = subprocess.run(
            [
                "grep",
                "-rn",
                f"-C{context}",
                "--include=" + path_glob.replace("**/", ""),
                symbol,
                repo_root,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        matches = proc.stdout.splitlines()
        return json.dumps(
            {
                "status": "ok",
                "ok": proc.returncode in (0, 1),
                "matches": matches[:400],
            }
        )
