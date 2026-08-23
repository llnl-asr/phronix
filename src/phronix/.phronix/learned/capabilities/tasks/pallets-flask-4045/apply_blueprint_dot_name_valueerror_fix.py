import re


def register(mcp):
    @mcp.tool()
    def apply_blueprint_dot_name_valueerror_fix(repo_root: str) -> str:
        """Edit <repo_root>/src/flask/blueprints.py so that:
        1. Blueprint.__init__ raises ValueError if `name` contains a dot.
        2. Blueprint.add_url_rule raises ValueError (not AssertionError) if
           `endpoint` contains a dot.
        3. Blueprint.add_url_rule raises ValueError (not AssertionError) if
           `view_func.__name__` contains a dot.

        This matches the upstream Flask 2.0.2 fix for the issue "Raise error
        when blueprint name contains a dot" (nested blueprints make every dot
        significant). Idempotent: returns a message and makes no change if the
        file already looks patched. Returns a status string describing what
        was changed or why nothing was changed.
        """
        path = f"{repo_root}/src/flask/blueprints.py"
        with open(path) as f:
            s = f.read()

        changed = []

        old_init = (
            '            root_path=root_path,\n'
            '        )\n'
            '        self.name = name'
        )
        new_init = (
            '            root_path=root_path,\n'
            '        )\n\n'
            '        if "." in name:\n'
            '            raise ValueError("\'name\' may not contain a dot \'.\' character.")\n\n'
            '        self.name = name'
        )
        if old_init in s:
            s = s.replace(old_init, new_init, 1)
            changed.append("name-dot check added to __init__")
        elif 'raise ValueError("\'name\' may not contain a dot' in s:
            changed.append("name-dot check already present")
        else:
            return "FAILED: __init__ anchor not found; file structure differs from expected"

        old_endpoint = (
            '        if endpoint:\n'
            '            assert "." not in endpoint, "Blueprint endpoints should not contain dots"\n'
            '        if view_func and hasattr(view_func, "__name__"):\n'
            '            assert (\n'
            '                "." not in view_func.__name__\n'
            '            ), "Blueprint view function name should not contain dots"'
        )
        new_checks = (
            '        if endpoint and "." in endpoint:\n'
            '            raise ValueError("\'endpoint\' may not contain a dot \'.\' character.")\n\n'
            '        if view_func and hasattr(view_func, "__name__"):\n'
            '            if "." in view_func.__name__:\n'
            '                raise ValueError("\'view_func\' name may not contain a dot \'.\' character.")'
        )
        if old_endpoint in s:
            s = s.replace(old_endpoint, new_checks, 1)
            changed.append("endpoint/view_func dot checks converted to ValueError")
        elif 'raise ValueError("\'endpoint\' may not contain a dot' in s:
            changed.append("endpoint/view_func checks already present")
        else:
            return "PARTIAL: name-dot check applied, but add_url_rule assert anchor not found (" + "; ".join(changed) + ")"

        with open(path, "w") as f:
            f.write(s)

        return "OK: " + "; ".join(changed)
