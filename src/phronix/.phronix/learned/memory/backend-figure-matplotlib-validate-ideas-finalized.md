---
name: backend-figure-matplotlib-validate-ideas-finalized
description: Validate-ideas stage finalized for backend-figure-matplotlib
metadata:
  type: project
---

---
name: backend-figure-matplotlib-validate-ideas-finalized
description: Validate-ideas stage finalized for backend-figure-matplotlib
metadata:
  type: project
---

The Validate-ideas stage assessed explored ideas for the DPI doubling bug on M1 Macs. No approach sufficiently resolved the target test `lib/matplotlib/tests/test_figure.py::test_unpickle_with_device_pixel_ratio`, which continues to fail. Additionally, the prior change introduced regressions in several SubplotMosaic tests (see feedback.md). Consequently, the stage concludes with no viable fix and recommends further investigation using an alternative mechanism that avoids DPI doubling on unpickle while preserving SubplotMosaic functionality.

**Why:** All evaluated ideas were insufficient and caused regressions, indicating the need for a different strategy.

**How to apply:** Future attempts should explore mechanisms that prevent DPI doubling during unpickling without impacting other backends. Avoid reusing the previous approach that led to SubplotMosaic regressions.
