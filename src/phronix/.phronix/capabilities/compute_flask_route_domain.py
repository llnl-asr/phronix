def register(mcp):
    @mcp.tool()
    def compute_flask_route_domain(host_matching: bool, rule_host: str, rule_subdomain: str, server_name: str) -> str:
        """Compute the display Domain string for one werkzeug Rule, matching
        flask's `routes` CLI fix (issue/PR #5063).

        Pass rule_host/rule_subdomain/server_name as empty string "" when the
        underlying attribute is None/unset (host is None off host_matching;
        subdomain defaults to "" when unset; SERVER_NAME may be unset -> None).

        Formula:
        - host_matching mode: domain = rule_host or server_name or ""
        - else: domain = f"{rule_subdomain}.{server_name}" if rule_subdomain and server_name
                else rule_subdomain if rule_subdomain
                else server_name or ""

        Returns the computed domain string (possibly empty).
        """
        if host_matching:
            return rule_host or server_name or ""
        if rule_subdomain and server_name:
            return f"{rule_subdomain}.{server_name}"
        if rule_subdomain:
            return rule_subdomain
        return server_name or ""
