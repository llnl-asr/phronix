import re


def register(mcp):
    @mcp.tool()
    def apply_dimensionless_function_fix(repo_root: str) -> str:
        """Edit sympy/physics/units/unitsystem.py so the Function branch of
        _collect_factor_and_dimension normalizes dimensionless argument
        dimensions to Dimension(1), mirroring the existing Pow branch logic.

        Returns a JSON string {status, path, changed}.
        """
        import json
        import os

        path = os.path.join(
            repo_root, "sympy", "physics", "units", "unitsystem.py"
        )
        with open(path, "r") as f:
            src = f.read()

        old = (
            "        elif isinstance(expr, Function):\n"
            "            fds = [self._collect_factor_and_dimension(\n"
            "                arg) for arg in expr.args]\n"
            "            return (expr.func(*(f[0] for f in fds)),\n"
            "                    *(d[1] for d in fds))\n"
        )
        new = (
            "        elif isinstance(expr, Function):\n"
            "            fds = [self._collect_factor_and_dimension(\n"
            "                arg) for arg in expr.args]\n"
            "            dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1])\n"
            "                    else d[1] for d in fds]\n"
            "            return (expr.func(*(f[0] for f in fds)), *dims)\n"
        )

        changed = old in src
        if changed:
            src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)

        return json.dumps({"status": "ok", "path": path, "changed": changed})
