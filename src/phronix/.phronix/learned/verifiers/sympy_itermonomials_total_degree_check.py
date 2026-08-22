"""Verifier for SymPy itermonomials total degree fix."""

SPEC = {
    "kind": "skill",
    "target": "sympy",
    "claim": "itermonomials correctly checks total degree (sum of powers) not max individual power when min_degrees is specified as integer",
    
    "assumptions": [
        {
            "name": "sympy_available",
            "detail": "sympy package is importable",
            "check": lambda ctx: _check_import()
        }
    ],
    
    "inputs": [
        {
            "name": "test_symbols",
            "required": True,
            "resolve": lambda ctx: _get_symbols()
        }
    ],
    
    "constraints": [
        {
            "name": "returns_all_degree_3_monomials",
            "detail": "min=max=3 with 3 variables returns all 10 monomials",
            "check": lambda ctx: _check_degree_3_case(ctx["test_symbols"])
        },
        {
            "name": "includes_mixed_monomials",
            "detail": "result includes x1*x2**2, x1*x2*x3, etc not just pure powers",
            "check": lambda ctx: _check_mixed_monomials(ctx["test_symbols"])
        },
        {
            "name": "respects_min_max_range",
            "detail": "min=2, max=3 returns only degrees 2 and 3",
            "check": lambda ctx: _check_range_case(ctx["test_symbols"])
        },
        {
            "name": "docstring_example_works",
            "detail": "itermonomials([x, y], 2, 1) returns expected monomials",
            "check": lambda ctx: _check_docstring_example(ctx["test_symbols"])
        }
    ],
    
    "invariants": [],
    
    "outputs": [
        {
            "name": "correct_count",
            "detail": "returns exactly 10 monomials for 3 vars degree 3",
            "check": lambda ctx: len(ctx.get("degree_3_result", [])) == 10
        }
    ]
}


def _check_import():
    try:
        import sympy
        from sympy.polys.monomials import itermonomials
        return True
    except ImportError as e:
        return False, str(e)


def _get_symbols():
    import sympy as sp
    x1, x2, x3 = sp.symbols('x1, x2, x3')
    x, y = sp.symbols('x, y')
    return {"x1": x1, "x2": x2, "x3": x3, "x": x, "y": y}


def _check_degree_3_case(symbols):
    import sympy as sp
    x1, x2, x3 = symbols["x1"], symbols["x2"], symbols["x3"]
    result = list(sp.itermonomials([x1, x2, x3], 3, min_degrees=3))
    
    # Store for output check
    import sys
    frame = sys._getframe()
    while frame:
        if "ctx" in frame.f_locals:
            frame.f_locals["ctx"]["degree_3_result"] = result
            break
        frame = frame.f_back
    
    # Check count is 10 (C(3+3-1, 3) = C(5,3) = 10)
    if len(result) != 10:
        return False, f"Expected 10 monomials, got {len(result)}: {result}"
    
    # Check all have total degree 3
    for m in result:
        degree = sum(m.as_powers_dict().values())
        if degree != 3:
            return False, f"Monomial {m} has degree {degree}, expected 3"
    
    return True, f"Correctly returns {len(result)} monomials all with degree 3"


def _check_mixed_monomials(symbols):
    import sympy as sp
    x1, x2, x3 = symbols["x1"], symbols["x2"], symbols["x3"]
    result = list(sp.itermonomials([x1, x2, x3], 3, min_degrees=3))
    
    # Check for presence of mixed monomials (not just x**3, y**3, z**3)
    result_strs = {str(m) for m in result}
    expected_mixed = ["x1*x2**2", "x1*x2*x3", "x1**2*x2", "x2*x3**2", "x1*x3**2"]
    
    found = []
    missing = []
    for m in expected_mixed:
        # Normalize: sympy might represent as x1**2*x2 or x2*x1**2
        if any(m in s or m.replace("*", "").replace("**", "") in s.replace("*", "").replace("**", "") 
               for s in result_strs):
            found.append(m)
        else:
            missing.append(m)
    
    if len(found) < 3:  # At least some mixed monomials
        return False, f"Missing mixed monomials. Found: {found}, result: {result_strs}"
    
    return True, f"Contains mixed monomials: {found}"


def _check_range_case(symbols):
    import sympy as sp
    x, y = symbols["x"], symbols["y"]
    result = list(sp.itermonomials([x, y], 3, min_degrees=2))
    
    # Check all degrees are in [2, 3]
    for m in result:
        degree = sum(m.as_powers_dict().values())
        if not (2 <= degree <= 3):
            return False, f"Monomial {m} has degree {degree}, expected 2 or 3"
    
    # Should have 7 monomials: x**2, xy, y**2 (deg 2) + x**3, x**2*y, x*y**2, y**3 (deg 3)
    if len(result) != 7:
        return False, f"Expected 7 monomials for range [2,3], got {len(result)}"
    
    return True, f"Range check passed: {len(result)} monomials with degrees 2-3"


def _check_docstring_example(symbols):
    import sympy as sp
    from sympy.polys.orderings import monomial_key
    x, y = symbols["x"], symbols["y"]
    
    result = sorted(sp.itermonomials([x, y], 2, 1), key=monomial_key('grlex', [y, x]))
    expected = [x, y, x**2, x*y, y**2]
    
    if result != expected:
        return False, f"Docstring example failed. Got {result}, expected {expected}"
    
    return True, f"Docstring example passes: {result}"


def register(mcp):
    """Register MCP verification tools."""
    pass  # Spec-only verifier
