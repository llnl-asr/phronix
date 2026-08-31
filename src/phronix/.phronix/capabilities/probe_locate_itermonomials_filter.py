def register(mcp):
    import re

    @mcp.tool()
    def probe_locate_itermonomials_filter(repo_root: str) -> str:
        """Find itermonomials' total_degree branch in sympy/polys/monomials.py.

        Returns the function source annotated with absolute line numbers,
        so the powers-filter condition (e.g. max(powers.values()) vs
        sum(powers.values())) can be located precisely before editing.
        """
        import os
        path = os.path.join(repo_root, "sympy", "polys", "monomials.py")
        with open(path, "r") as f:
            lines = f.readlines()

        start = None
        end = None
        for i, line in enumerate(lines):
            if start is None and re.match(r"\s*def itermonomials\b", line):
                start = i
            elif start is not None and re.match(r"\s*def \w+", line) and i > start:
                end = i
                break
        if start is None:
            return "ERROR: def itermonomials not found in %s" % path
        if end is None:
            end = len(lines)

        out = []
        out.append("FILE: %s" % path)
        for i in range(start, end):
            out.append("%d: %s" % (i + 1, lines[i].rstrip("\n")))
        return "\n".join(out)
