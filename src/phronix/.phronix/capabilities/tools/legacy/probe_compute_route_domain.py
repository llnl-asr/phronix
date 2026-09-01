def register(mcp):
    @mcp.tool()
    def probe_compute_route_domain(subdomain: str, server_name: str) -> str:
        """Compute the domain string for a route.

        Given a Werkzeug Rule's ``subdomain`` (may be empty string or None)
        and the Flask app's ``SERVER_NAME`` config value (may be empty
        string or None), return the domain that should be displayed for
        that route: ``f"{subdomain}.{server_name}"`` when subdomain is set,
        otherwise ``server_name`` (or "" if that is also unset).
        """
        subdomain = subdomain or ""
        server_name = server_name or ""
        if subdomain:
            return f"{subdomain}.{server_name}" if server_name else subdomain
        return server_name
