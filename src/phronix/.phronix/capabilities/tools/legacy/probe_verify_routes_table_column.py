def register(mcp):
    @mcp.tool()
    def probe_verify_routes_table_column(table_text: str, column_name: str, expected_values: str) -> str:
        """Verify a text table produced by a CLI command has a given column with expected values.

        ``table_text`` is the raw stdout of the command (header row, a
        separator row of dashes, then data rows, whitespace-aligned).
        ``column_name`` is the header to look for (case-insensitive).
        ``expected_values`` is a JSON array of strings expected to appear,
        in order, in that column across the data rows.

        Returns a JSON object: {"status": "ok"|"mismatch"|"column_not_found",
        "found_values": [...], "expected_values": [...]}.
        """
        import json

        lines = [line for line in table_text.splitlines() if line.strip()]
        if not lines:
            return json.dumps({"status": "mismatch", "found_values": [], "expected_values": json.loads(expected_values)})

        header = lines[0]
        col_start = header.lower().find(column_name.lower())
        if col_start == -1:
            return json.dumps({"status": "column_not_found", "found_values": [], "expected_values": json.loads(expected_values)})

        headers = header.split()
        col_index = None
        pos = 0
        for i, h in enumerate(headers):
            pos = header.find(h, pos)
            if pos == col_start:
                col_index = i
                break
            pos += len(h)

        data_lines = [l for l in lines[1:] if not set(l.strip()) <= {"-", " "}]
        found = []
        for line in data_lines:
            parts = line.split()
            if col_index is not None and col_index < len(parts):
                found.append(parts[col_index])

        expected = json.loads(expected_values)
        status = "ok" if found == expected else "mismatch"
        return json.dumps({"status": status, "found_values": found, "expected_values": expected})
