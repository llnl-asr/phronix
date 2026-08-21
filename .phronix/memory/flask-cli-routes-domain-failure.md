---
name: flask-cli-routes-domain-failure
description: Adding Domain column broke existing tests for flask routes command
metadata:
  type: project
---

**Why:** The added Domain column changes output formatting and column widths, causing test failures that expect three columns.
**How to apply:** Ensure the Domain column is only added when at least one rule has a subdomain or host, and keep original layout otherwise.
**Context:** Tests `test_simple`, `test_sort`, `test_all_methods`, `test_subdomain`, `test_host` all failed after the change.
