---
name: flask-client-open-as-tuple-fix
description: Fixed FlaskClient.open compatibility with newer Werkzeug
metadata:
  type: project
---

Implemented change in src/flask/testing.py to drop the now‑unsupported `as_tuple` argument from the call to `super().open`. Added detailed comment explaining the reason and impact. This resolves the TypeError that caused many tests to fail (attempt‑2) and restores full test suite success.

**Why:** Newer Werkzeug versions removed `as_tuple`; keeping it caused a crash. The argument was unnecessary for the test suite.

**How to apply:** Apply the patch in src/flask/testing.py.

**Verification:** All tests now pass (`70 passed, 1 xfailed`).
