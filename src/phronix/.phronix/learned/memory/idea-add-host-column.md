---
name: idea-add-host-column
description: Attempt to add Host column to flask routes when host_matching enabled
metadata:
  type: project
---

**Why:** Explore whether adding a Host column works and its impact on tests.
**How to apply:** The probe showed the column appears but values are empty, causing test failures.
**Finding:** Adding Host column with host_matching true results in empty values and breaks existing route tests.
