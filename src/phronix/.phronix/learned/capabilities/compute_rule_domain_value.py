def register(mcp):
    @mcp.tool()
    def compute_rule_domain_value(subdomain: str = "", host: str = "", host_matching: bool = False, server_name: str = "", full_domain: bool = False) -> str:
        """Compute the domain string for one route rule.

        Args:
            subdomain: rule.subdomain value (may be empty/None-as-"").
            host: rule.host value, used when host_matching is True.
            host_matching: whether the app's url_map uses host_matching.
            server_name: app.config.get("SERVER_NAME") or "".
            full_domain: if True, combine subdomain with server_name
                (e.g. "admin.test.local") instead of returning the bare
                subdomain fragment ("admin").

        Returns:
            The computed domain string (may be "").
        """
        if host_matching:
            return host or ""
        if not full_domain:
            return subdomain or ""
        if subdomain:
            return f"{subdomain}.{server_name}" if server_name else subdomain
        return server_name or ""
