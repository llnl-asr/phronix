import json
import re


def register(mcp):
    @mcp.tool()
    def locate_unitsystem_function_branch(repo_root: str) -> str:
        """Find the `elif isinstance(expr, Function)` branch inside
        _collect_factor_and_dimension in
        sympy/physics/units/unitsystem.py, and check whether `Dimension`
        is already imported in that file. Returns JSON
        {status, file, method_start_line, function_branch, dimension_imported}
        where function_branch is {start_line, end_line, text} for the
        Function elif block (best-effort: from the 'isinstance(expr, Function)'
        line up to the next 'elif'/'else' at the same indentation or end of
        method), or null if not found.
        """
        path = f"{repo_root.rstrip('/')}/sympy/physics/units/unitsystem.py"
        with open(path) as f:
            lines = f.readlines()

        dimension_imported = any(
            re.search(r"\bimport\b.*\bDimension\b", l) or
            re.search(r"^\s*from .*dimensions.* import .*Dimension", l)
            for l in lines
        )

        method_start = None
        for i, l in enumerate(lines):
            if "_collect_factor_and_dimension" in l and l.lstrip().startswith("def "):
                method_start = i
                break

        function_branch = None
        if method_start is not None:
            branch_start = None
            for i in range(method_start, len(lines)):
                if "isinstance(expr, Function)" in lines[i]:
                    branch_start = i
                    break
            if branch_start is not None:
                indent = len(lines[branch_start]) - len(lines[branch_start].lstrip())
                branch_end = len(lines) - 1
                for j in range(branch_start + 1, len(lines)):
                    stripped = lines[j].lstrip()
                    cur_indent = len(lines[j]) - len(stripped)
                    if stripped and cur_indent <= indent and (
                        stripped.startswith("elif ") or stripped.startswith("else")
                        or (cur_indent < indent)
                    ):
                        branch_end = j - 1
                        break
                function_branch = {
                    "start_line": branch_start + 1,
                    "end_line": branch_end + 1,
                    "text": "".join(lines[branch_start:branch_end + 1]),
                }

        return json.dumps(
            {
                "status": "ok",
                "file": path,
                "method_start_line": (method_start + 1) if method_start is not None else None,
                "function_branch": function_branch,
                "dimension_imported": dimension_imported,
            }
        )
