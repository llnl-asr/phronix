import json
import os


def register(mcp):
    @mcp.tool()
    def apply_strict_dimensionless_function_check(repo_root: str) -> str:
        """Edit sympy/physics/units/unitsystem.py so the Function branch of
        _collect_factor_and_dimension raises ValueError when any argument's
        dimension is not dimensionless, and otherwise returns Dimension(1)
        as the function's overall dimension.

        Returns a JSON string {status, path, changed}.
        """
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
            "            for f in fds:\n"
            "                if not self.get_dimension_system().is_dimensionless(f[1]):\n"
            "                    raise ValueError(\n"
            "                        'Function %s expects dimensionless arguments, got %s'\n"
            "                        % (expr.func, f[1]))\n"
            "            return (expr.func(*(f[0] for f in fds)),\n"
            "                    *(Dimension(1) for f in fds))\n"
        )

        changed = old in src
        if changed:
            src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)

        return json.dumps({"status": "ok", "path": path, "changed": changed})
