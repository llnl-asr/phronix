import re


def register(mcp):
    @mcp.tool()
    def apply_normpath_fix_expand_modules(repo_path: str) -> str:
        """Insert `element = os.path.normpath(element)` as the first line of
        _is_ignored_file's body in <repo_path>/pylint/lint/expand_modules.py,
        fixing pylint#7080 (ignore-paths not honored under --recursive=y when
        walking the current directory, due to unnormalized './'-prefixed paths
        failing to match anchored ignore-paths regexes). Idempotent: if the
        normpath line is already present, does nothing and reports that.
        Returns a status string describing what happened.
        """
        path = f"{repo_path}/pylint/lint/expand_modules.py"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if "element = os.path.normpath(element)" in content:
            return f"already applied: {path}"

        pattern = re.compile(
            r"(def _is_ignored_file\([^)]*\)[^\n]*:\n(?:\s*\"\"\".*?\"\"\"\n)?)(\s*)"
        )
        m = pattern.search(content, re.DOTALL)
        if not m:
            # Fallback: DOTALL wasn't passed to compile, retry properly.
            pattern = re.compile(
                r"(def _is_ignored_file\([^)]*\)[^\n]*:\n(?:\s*\"\"\".*?\"\"\"\n)?)(\s*)",
                re.DOTALL,
            )
            m = pattern.search(content)
        if not m:
            return f"ERROR: could not locate _is_ignored_file definition in {path}"

        indent = m.group(2)
        insertion = m.group(1) + indent + "element = os.path.normpath(element)\n" + indent
        new_content = content[: m.start()] + insertion + content[m.end() :]

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"patched: {path}"
