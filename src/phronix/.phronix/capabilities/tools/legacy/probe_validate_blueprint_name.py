def register(mcp):
    @mcp.tool()
    def probe_validate_blueprint_name(name: str) -> bool:
        """Return True if Blueprint(name) raises ValueError for dot in name."""
        from flask import Blueprint
        try:
            Blueprint(name, __name__)
            return False
        except ValueError:
            return True