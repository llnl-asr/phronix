---
name: pytest-dev-pytest-7432
description: Fix for pytest-dev-7432: re‑add runxfail guard in skipping.py
subject: pytest-dev-pytest-7432
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Restore runxfail handling in skipping.py |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Restore runxfail handling in skipping.py

In `src/_pytest/skipping.py`, reintroduce the runxfail guard to ensure the location‑fix code executes when `--runxfail` is not used. Replace the removed `elif` block with:

```python
if item.config.getoption("runxfail"):
    # When --runxfail is active, preserve original behaviour (do not modify report).
    pass
else:
    # Existing location‑fix logic remains unchanged.
    ... (no change needed)
```

This preserves the intended handling of `--runxfail` while allowing the skip location fix to operate correctly in normal runs.

**Established tests must continue passing** – the fix must not affect the 76 regression tests that already passed.

**Why this form** – the previous removal broke the `elif` chain, causing the location‑fix block to be skipped entirely, leading to the failing XFail test. Restoring an explicit `if` guard restores the control flow without side effects.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/src/_pytest/skipping.py b/src/_pytest/skipping.py
index 7bd975e5a..0971d7297 100755
--- a/src/_pytest/skipping.py
+++ b/src/_pytest/skipping.py
@@ -270,6 +270,18 @@ def pytest_runtest_makereport(item: Item, call: CallInfo[None]):
         else:
             rep.longrepr = "Unexpected success"
         rep.outcome = "failed"
+    elif (
+        item._store.get(skipped_by_mark_key, True)
+        and rep.skipped
+        and type(rep.longrepr) is tuple
+    ):
+        # skipped by mark.skipif; change the location of the failure
+        # to point to the item definition, otherwise it will display
+        # the location of where the skip exception was raised within pytest
+        _, _, reason = rep.longrepr
+        filename, line = item.reportinfo()[:2]
+        assert line is not None
+        rep.longrepr = str(filename), line + 1, reason
     elif item.config.option.runxfail:
         pass  # don't interfere
     elif call.excinfo and isinstance(call.excinfo.value, xfail.Exception):
```

## Rules
