def register(mcp):
    @mcp.tool()
    def probe_routes_domain_column_logic(rules: str, host_matching: bool) -> str:
        """Compute has_domain and per-rule domain values for flask's `routes` command.

        rules: JSON array of objects, each with "host" and "subdomain" keys
            (either may be null/empty), one per werkzeug Rule.
        host_matching: current_app.url_map.host_matching.

        Returns JSON: {"has_domain": bool, "header": "Host"|"Subdomain",
        "domains": [per-rule domain string, "" if none]}.

        Mirrors the upstream fix in flask.cli.routes_command: has_domain is
        True iff any rule's (host if host_matching else subdomain) is
        truthy. The header is exactly "Host" when host_matching else
        "Subdomain" -- never "Domain". When has_domain is False, callers
        must omit the column entirely (do not just leave it blank) so
        Endpoint stays column 0, matching test_simple/test_sort.
        """
        import json

        parsed = json.loads(rules)
        domains = []
        has_domain = False
        for rule in parsed:
            value = rule.get("host") if host_matching else rule.get("subdomain")
            value = value or ""
            if value:
                has_domain = True
            domains.append(value)
        header = "Host" if host_matching else "Subdomain"
        return json.dumps({"has_domain": has_domain, "header": header, "domains": domains})
