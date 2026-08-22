---
name: pallets-flask-4045-attempt-2-result
description: Outcome of attempt 2 for dotted blueprint name fix
metadata:
  type: project
---

Attempt 2 added error for dotted blueprint names but introduced regressions in test_client related tests because it altered the Flask testing Cookie class signature. Target tests for blueprints still failing; many regression tests now error due to Cookie __init__ mismatch.
**Why:** The fix modified shared code impacting Cookie initialization, causing TypeError in multiple tests.
