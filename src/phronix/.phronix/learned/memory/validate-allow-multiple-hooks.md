---
name: validate-allow-multiple-hooks
description: Validation outcome for supporting multiple hooks in Request
metadata:
  type: project
---

The issue "Allow lists in the dict values of the hooks argument" was reviewed. The proposed fix is to update ``requests/models.py`` so that ``Request.__init__`` accepts a list (or tuple) of callables for each hook key and invokes each when the hook is consumed. This change resolves the current limitation where only a single hook function can be specified, leading to failures when multiple hooks are needed.

**Why:** The current implementation wraps a list of callables in another list, causing a ``list`` not callable error during hook execution. Supporting multiple hooks improves extensibility and aligns with typical usage patterns.

**How to apply:** Modify the ``Request.__init__`` method to detect iterable hook values and iterate over them when executing the hook. Ensure backward compatibility with single-callable values. Add unit tests covering multiple-hook registration and execution.

The validation confirms this fix is necessary and feasible. The next stage should implement the code changes and add corresponding tests.

[[allow-multiple-hooks]]
