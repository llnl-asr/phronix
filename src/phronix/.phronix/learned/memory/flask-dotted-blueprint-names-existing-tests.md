---
name: flask-dotted-blueprint-names-existing-tests
description: Flask codebase has existing tests that create blueprints with dotted names, requiring migration before dot validation can be enforced
metadata:
  type: reference
---

**Existing Tests Using Dotted Blueprint Names:**

1. `tests/test_blueprints.py::test_dotted_names` (lines 257-258)
   - Creates `flask.Blueprint("myapp.frontend", __name__)`
   - Creates `flask.Blueprint("myapp.backend", __name__)`
   - Tests url_for with dotted blueprint names

2. `tests/test_basic.py::test_inject_blueprint_url_defaults` (line 1634)
   - Creates `flask.Blueprint("foo.bar.baz", __name__, template_folder="template")`
   - Tests URL defaults injection with deeply nested dotted name

**Implication:** Adding ValueError validation `if "." in name: raise ValueError()` in Blueprint.__init__() will break these tests. These tests would need to be updated to either:
- Use non-dotted names (if dotted names are no longer supported)
- Be marked as deprecation tests (if dots are being phased out)
- Test the new nested blueprint registration API (if that's the replacement)

**Why This Matters:** A fix that makes all target tests pass but breaks existing regression tests is incomplete. The validation needs to account for backwards compatibility or the tests need updating as part of the same change.
