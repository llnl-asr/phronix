import json


def register(mcp):
    @mcp.tool()
    def probe_apply_text_replacement(file_path: str, replacements: str) -> str:
        """Apply exact string replacements to *file_path*.

        *replacements* is a JSON array of {old, new, count?} objects, applied
        in order. Each `old` must be found in the file exactly `count` times
        (default: at least once); if not, that replacement is skipped and
        reported as failed rather than silently applying elsewhere.

        Returns JSON {status, applied: [{old, new, occurrences}], failed: [str]}.
        """
        with open(file_path, "r") as f:
            text = f.read()

        specs = json.loads(replacements)
        applied = []
        failed = []
        for spec in specs:
            old = spec["old"]
            new = spec["new"]
            occurrences = text.count(old)
            if occurrences == 0:
                failed.append(old)
                continue
            text = text.replace(old, new)
            applied.append({"old": old, "new": new, "occurrences": occurrences})

        with open(file_path, "w") as f:
            f.write(text)

        return json.dumps({"status": "ok", "applied": applied, "failed": failed})
