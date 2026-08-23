---
name: psf-requests-863-validate-ideas-finalized
description: Validate ideas stage for psf__requests-863 completed
metadata:
  type: project
---

The validate-ideas stage for the psf__requests-863 issue was completed. The change introduces support for passing a list of hook functions in the `hooks` argument of `Request.__init__`, allowing multiple hooks per event without manual registration. This resolves the issue where passing a list caused errors because the code treated the list as a single non-callable hook.

**Why:** Enables proper usage of multiple hooks, simplifying API and fixing the bug described in issue.md.

**How to apply:** `Request.__init__` now iterates over hook values and registers each callable when a list or tuple is provided, preserving existing behavior for single hooks.

[[psf-requests-863-validate-ideas]]
