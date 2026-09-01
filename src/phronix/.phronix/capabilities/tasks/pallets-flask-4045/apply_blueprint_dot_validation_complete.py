import re

NAME_CHECK = '''        if "." in name:
            raise ValueError("'name' may not contain a dot '.' character.")

'''

def register(mcp):
    @mcp.tool()
    def apply_blueprint_dot_validation_complete(repo_root: str) -> str:
        """Insert the Blueprint name dot check and convert the add_url_rule endpoint/view_func dot asserts to ValueError. Idempotent."""
        path = f"{repo_root}/src/flask/blueprints.py"
        with open(path) as f:
            src = f.read()
        changes = []

        if "'name' may not contain a dot" not in src:
            marker = "        self.name = name\n"
            idx = src.find(marker)
            if idx == -1:
                return "FAILED: could not find 'self.name = name' marker"
            src = src[:idx] + NAME_CHECK + src[idx:]
            changes.append("inserted name dot check")
        else:
            changes.append("name dot check already present")

        endpoint_assert = re.search(r'[ \t]*assert ["\']\.["\'] not in endpoint,.*\n', src)
        if endpoint_assert:
            indent = re.match(r'[ \t]*', endpoint_assert.group(0)).group(0)
            replacement = (
                f'{indent}if endpoint and "." in endpoint:\n'
                f'{indent}    raise ValueError("\'endpoint\' may not contain a dot \'.\' character.")\n'
            )
            src = src[:endpoint_assert.start()] + replacement + src[endpoint_assert.end():]
            changes.append("converted endpoint assert to ValueError")
        elif "'endpoint' may not contain a dot" in src:
            changes.append("endpoint check already converted")

        viewfunc_assert = re.search(r'[ \t]*assert ["\']\.["\'] not in view_func\.__name__,.*\n', src)
        if viewfunc_assert:
            indent = re.match(r'[ \t]*', viewfunc_assert.group(0)).group(0)
            replacement = (
                f'{indent}if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:\n'
                f'{indent}    raise ValueError("\'view_func\' name may not contain a dot \'.\' character.")\n'
            )
            src = src[:viewfunc_assert.start()] + replacement + src[viewfunc_assert.end():]
            changes.append("converted view_func assert to ValueError")
        elif "'view_func' name may not contain a dot" in src:
            changes.append("view_func check already converted")

        with open(path, "w") as f:
            f.write(src)
        return "OK: " + "; ".join(changes)
