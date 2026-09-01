def register(mcp):
    @mcp.tool()
    def compute_rule_domain_formula() -> str:
        """Return the canonical, tested formula for computing the domain
        string of a werkzeug Rule inside Flask's `routes_command`, without
        hand-rolling subdomain/host string concatenation.

        Reference implementation (paste/adapt into src/flask/cli.py):

            host_matching = current_app.url_map.host_matching
            adapter = current_app.create_url_adapter(None)
            def get_domain(rule):
                if adapter is None:
                    return ""
                key = rule.host if host_matching else rule.subdomain
                return adapter.get_host(key)

        Notes:
        - create_url_adapter(None) binds using SERVER_NAME with no request
          and returns None if SERVER_NAME is not configured -- that case
          must be handled (empty domain / no Domain column), not fabricated.
        - adapter.get_host already normalizes an empty-string subdomain to
          the bare server_name (no leading dot) and handles host_matching
          mode by treating the key as a full host. Do not re-implement this
          logic with an f-string; it silently mishandles empty subdomain
          and host_matching.
        - rule.subdomain is never None after Rule.bind (defaults to "").
        """
        return (
            "host_matching = current_app.url_map.host_matching\n"
            "adapter = current_app.create_url_adapter(None)\n"
            "def get_domain(rule):\n"
            "    if adapter is None:\n"
            "        return \"\"\n"
            "    key = rule.host if host_matching else rule.subdomain\n"
            "    return adapter.get_host(key)\n"
        )
