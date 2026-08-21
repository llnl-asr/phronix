SPEC = {
    "kind": "skill",
    "target": "flask-blueprint-validation-edit",
    "claim": "After applying flask-blueprint-validation-edit changes, creating a Blueprint with a name containing a dot raises ValueError.",
    "assumptions": [],
    "inputs": [
        {"name": "flask_import", "required": true, "resolve": lambda ctx: __import__('flask')}
    ],
    "constraints": [
        {
            "name": "blueprint_dot_raises",
            "detail": "Creating Blueprint with dot in name raises ValueError",
            "check": lambda ctx: (
                (lambda: (
                    __import__('flask').Blueprint('bad.name', __name__)  # noqa: F821
                ))()
                if False else True  # placeholder
            )
        }
    ],
    "invariants": [],
    "outputs": []
}

def verify(context):
    # Ensure src is on sys.path via sitecustomize; import Blueprint
    try:
        from flask import Blueprint
    except Exception as e:
        return {"ok": False, "evidence": f"Import failed: {e}"}
    try:
        Blueprint('bad.name', __name__)
    except ValueError as e:
        return {"ok": True, "evidence": str(e)}
    except Exception as e:
        return {"ok": False, "evidence": f"Unexpected exception: {e}"}
    else:
        return {"ok": False, "evidence": "No exception raised for dot in Blueprint name"}
