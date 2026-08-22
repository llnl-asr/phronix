---
name: normalize-ignore-paths-reconcile-failure
description: Recording why normalize-ignore-paths research did not produce a patch
metadata:
  type: feedback
---

The previous attempt to address ignore-paths handling in pylint did not generate any code changes. **Why:** The research identified the need to normalize file paths before ignore pattern checks, but no concrete implementation was provided, so the tool could not produce a patch. **How to apply:** Implement the normalization step in pylint's file collection logic (e.g., normalize subfile paths before applying ignore patterns) and add appropriate unit tests to verify the change.
