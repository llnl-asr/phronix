import json


def register(mcp):
    @mcp.tool()
    def apply_regex_replace(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Replace old_string with new_string in file_path. Fails if old_string
        is not found, or (when replace_all is False) if it is not unique.
        Returns JSON {status, ok, replacements}. Use this to apply a small,
        exact source-code edit (e.g. changing a regex suffix) without
        rewriting the whole file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return json.dumps({"status": "error", "ok": False, "error": str(e)})

        count = content.count(old_string)
        if count == 0:
            return json.dumps({"status": "error", "ok": False, "error": "old_string not found"})
        if count > 1 and not replace_all:
            return json.dumps({"status": "error", "ok": False, "error": f"old_string not unique ({count} occurrences); pass replace_all=true"})

        new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            return json.dumps({"status": "error", "ok": False, "error": str(e)})

        return json.dumps({"status": "ok", "ok": True, "replacements": count if replace_all else 1})
