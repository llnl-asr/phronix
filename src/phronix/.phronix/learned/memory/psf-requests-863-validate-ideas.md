---
name: psf-requests-863-validate-ideas
description: Validate ideas stage for psf__requests-863: allow list of hooks
metadata:
  type: project
---

Implemented support for list values in the hooks argument of Request.__init__. Previously, passing a list of hook functions resulted in the list being stored as a single non-callable hook, causing failures when multiple hooks were needed.

**Why:** The issue required allowing multiple hooks per event without requiring manual registration calls. Supporting lists simplifies usage and aligns with expected behavior.

**How to apply:** The Request.__init__ now iterates over hook values; if a value is a list or tuple, each hook is registered individually via register_hook. Existing single-hook behavior remains unchanged.

[[psf-requests-863-validate-ideas]]
