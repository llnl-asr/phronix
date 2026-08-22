import os, sys

def _test_error():
    # Ensure repository's sympy code is in sys.path
    repo_root = os.path.abspath(os.path.join(os.getcwd(), "repo"))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from sympy import exp
        from sympy.physics.units import second, ohm, farad
        from sympy.physics.units.systems.si import SI
    except Exception as e:
        return False, f"Import error: {e}"
    expr = second/(ohm*farad)
    buggy_expr = 100 + exp(expr)
    try:
        SI._collect_factor_and_dimension(buggy_expr)
    except ValueError as ve:
        if "Dimension of" in str(ve):
            return True, "ValueError raised as expected"
        else:
            return False, f"Unexpected ValueError message: {ve}"
    except Exception as e:
        return False, f"Unexpected exception: {e}"
    else:
        return False, "No exception raised"

SPEC = {
    "kind": "skill",
    "target": "sympy-unit-system-fix",
    "claim": "Adding sitecustomize.py does not fix the dimensionless error in SI._collect_factor_and_dimension; the error persists when calling SI._collect_factor_and_dimension on expressions with non-dimensionless arguments (e.g., exp(second/(farad*ohm))).",
    "assumptions": [
        {"name": "sympy_importable", "detail": "sympy package can be imported", "check": lambda ctx: __import__("sympy") is not None}
    ],
    "inputs": [],
    "constraints": [
        {"name": "error_raised", "detail": "SI._collect_factor_and_dimension raises ValueError for non-dimensionless argument", "check": lambda ctx: _test_error()[0]}
    ],
    "invariants": [],
    "outputs": []
}
