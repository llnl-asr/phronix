---
name: flask-testing-cookie-jar-replacement
description: Use Werkzeug CookieJar instead of custom Cookie stub in Flask testing
metadata:
  type: project
---

**Why:** The custom `Cookie` stub in `src/flask/testing.py` does not match the expected signature of Werkzeug's `Cookie`, causing `TypeError` during tests.
**How to apply:** Replace the custom stub with `from werkzeug.test import CookieJar` and instantiate with `self.cookie_jar = CookieJar()`.

[[flask-testing-cookie-jar-replacement]]
