---
name: backend-figure-matplotlib-validate-ideas
description: Validate-ideas stage findings for backend-figure-matplotlib
metadata:
  type: project
---

The stage assessed the explored ideas and found none that sufficiently address the DPI unpickle bug. It confirmed that the target test `lib/matplotlib/tests/test_figure.py::test_unpickle_with_device_pixel_ratio` still fails. Additionally, the previous change introduced regressions in several SubplotMosaic tests (listed in feedback.md). No viable approach was established; further investigation is needed.

**Why:** The stage's purpose was to judge whether ideas could change the outcome. All ideas were insufficient, and regressions indicate the change broke other functionality.

**How to apply:** Focus next attempts on a different mechanism to prevent DPI doubling on unpickle, ensuring no impact on SubplotMosaic functionality. Avoid reusing the prior approach that caused regressions.
