def register(mcp):
    @mcp.tool()
    def probe_fix_max_to_sum_powers_filter(repo_root: str) -> str:
        """Fix itermonomials' total-degree bug in sympy/polys/monomials.py.

        Replaces every occurrence of `max(powers.values())` with
        `sum(powers.values())` inside the file, which corrects both the
        commutative and non-commutative total_degree branches (the bug:
        filtering by the largest single exponent instead of total degree).
        Returns how many replacements were made, or an error if none found
        (meaning the fix may already be applied or the code has changed).
        """
        import os
        path = os.path.join(repo_root, "sympy", "polys", "monomials.py")
        with open(path, "r") as f:
            content = f.read()

        old = "max(powers.values())"
        new = "sum(powers.values())"
        count = content.count(old)
        if count == 0:
            return "NO_MATCH: '%s' not found in %s (already fixed or code changed)" % (old, path)

        content = content.replace(old, new)
        with open(path, "w") as f:
            f.write(content)
        return "OK: replaced %d occurrence(s) of '%s' with '%s' in %s" % (count, old, new, path)
