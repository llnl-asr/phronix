import subprocess
import sys

_SNIPPET = '''
import re, sys
sys.path.insert(0, {repo_path!r})
from pylint.lint import PyLinter

linter = PyLinter()
linter.config.ignore = {ignore!r}
linter.config.ignore_patterns = [re.compile(p) for p in {ignore_patterns!r}]
linter.config.ignore_paths = [re.compile(p) for p in {ignore_paths!r}]
result = sorted(linter._discover_files([{target!r}]))
for r in result:
    print(r)
'''

def register(mcp):
    @mcp.tool()
    def check_discover_files_ignore_filtering(
        repo_path: str,
        target: str,
        ignore: list = None,
        ignore_patterns: list = None,
        ignore_paths: list = None,
    ) -> str:
        """Run PyLinter()._discover_files([target]) in a subprocess with the
        given ignore / ignore_patterns (regex strings) / ignore_paths (regex
        strings) config set, using repo_path's pylint on sys.path. Returns the
        newline-separated list of files that were yielded (i.e. NOT filtered
        out), so callers can diff against the expected exclusion set."""
        code = _SNIPPET.format(
            repo_path=repo_path,
            ignore=ignore or [],
            ignore_patterns=ignore_patterns or [],
            ignore_paths=ignore_paths or [],
            target=target,
        )
        try:
            out = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
            )
        except Exception as e:
            return f"error: {e}"
        if out.returncode != 0:
            return f"error running snippet:\\n{out.stderr}"
        return out.stdout
