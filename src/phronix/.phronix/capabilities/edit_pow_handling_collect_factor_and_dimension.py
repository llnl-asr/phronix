def register(mcp):
    @mcp.tool()
    def edit_pow_handling_collect_factor_and_dimension():
        """Edit sympy/physics/units/unitsystem.py to fix Pow handling.
        Replaces the return line in the Pow case to use exponent directly.
        """
        import pathlib, re
        path = pathlib.Path('sympy/physics/units/unitsystem.py')
        content = path.read_text(encoding='utf-8')
        # pattern to match the return line in Pow handling
        pattern = r"return factor \*\* expr\.exp, dim \*\* \(exp_factor \* exp_dim\)"
        replacement = "return factor ** expr.exp, dim ** expr.exp"
        new_content, count = re.subn(pattern, replacement, content)
        if count == 0:
            raise RuntimeError('Pattern not found for Pow handling edit')
        path.write_text(new_content, encoding='utf-8')
