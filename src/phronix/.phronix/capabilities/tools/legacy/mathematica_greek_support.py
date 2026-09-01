def register(mcp):
    @mcp.tool()
    def mathematica_greek_support(s):
        """Parse Greek characters in Mathematica expressions.
        Extends MathematicaParser._atom_conversions with Greek letters.
        """
        from sympy import symbols
        parser = MathematicaParser()
        # add Greek letters to atom conversions
        greek = [
            'Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta',
            'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Omicron', 'Pi',
            'Rho', 'Sigma', 'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega',
            'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta',
            'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi',
            'rho', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega'
        ]
        for g in greek:
            parser._atom_conversions[g] = symbols(g)
        return parser.parse(s)
