def register(mcp):
    @mcp.tool()
    def add_domain_column_to_cli_table(source: str, always_show: bool = True) -> str:
        """Return guidance + a regex-friendly description of edits needed to add a
        'Domain' column to flask's `routes_command` table renderer.

        This does not blindly rewrite arbitrary source (table-building code is
        too varied to regex safely); instead it returns the concrete edit plan
        as JSON so a follow-up Edit call can apply it precisely.

        Args:
            source: the current contents of the routes_command function body.
            always_show: if True, Domain column is always included; if False,
                only included when at least one rule has a non-empty domain.

        Returns:
            JSON string describing the four edit points: headers tuple,
            width calculation, row format string, and the echo loop zip/format
            call, plus the always_show condition to wrap them in if requested.
        """
        import json
        plan = {
            "headers_edit": "Insert 'Domain' into the headers tuple, keeping Endpoint/Methods/Rule order as documented by the issue's example table.",
            "widths_edit": "Add a width variable: domain_width = max(len(d) for d in (['Domain'] + domains)) if domains else len('Domain')",
            "row_format_edit": "Extend the row format string to include a 4th '{:<domain_width}' (or last column, no padding) field for Domain.",
            "echo_loop_edit": "Zip domains alongside rule/methods/endpoint when building each row's values passed to row.format(...)",
            "always_show": always_show,
            "conditional_note": "If always_show is False, wrap the above 4 edits in `if any(domains):` and fall back to the original 3-column layout otherwise." if not always_show else "",
        }
        return json.dumps(plan)
