def register(mcp):
    @mcp.tool()
    def extend_table_row_format(headers_csv: str, rows_json: str) -> str:
        """Given headers as a comma-separated string and rows_json as a JSON
        array of arrays (same column count as headers), compute the width
        of each column (max of header length and all cell lengths in that
        column) and return a str.format row template like
        '{0:<10}{1:<8}{2:<20}' along with the widths, ready to use for a
        fixed-width CLI table such as flask's `routes_command` output."""
        import json
        headers = [h.strip() for h in headers_csv.split(",")]
        rows = json.loads(rows_json)
        widths = []
        for i, h in enumerate(headers):
            col_vals = [str(r[i]) for r in rows] if rows else []
            widths.append(max([len(h)] + [len(v) for v in col_vals]))
        template = "".join(f"{{{i}:<{w}}}" for i, w in enumerate(widths))
        return json.dumps({"widths": widths, "row_format": template})
