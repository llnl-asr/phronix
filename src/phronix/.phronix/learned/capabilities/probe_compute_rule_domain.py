def register(mcp):
    @mcp.tool()
    def probe_compute_rule_domain(subdomain: str, server_name: str) -> str:
        """Compute the Domain column value for a werkzeug Rule.

        subdomain: rule.subdomain, or "" if the rule has none.
        server_name: app.config.get("SERVER_NAME") or "" if unset.

        Joins subdomain and server_name with '.' when both are present;
        falls back to whichever one is present; returns "" if neither is set.
        Mirrors flask.cli.routes_command's get_rule_domain helper.
        """
        if subdomain:
            if server_name:
                return f"{subdomain}.{server_name}"
            return subdomain
        return server_name or ""
