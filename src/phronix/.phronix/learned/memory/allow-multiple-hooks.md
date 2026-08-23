---
name: allow-multiple-hooks
description: Support multiple hook functions per hook in Request initialization
metadata:
  type: project
---

Allow lists of hook functions in the dict values of the ``hooks`` argument for ``requests.models.Request``.

**Why:** Currently ``Request.__init__`` only accepts a single callable per hook. Passing a list results in the list being wrapped in another list, causing a ``list`` not callable error when the hook is consumed. This limits extensibility and makes it impossible to register multiple hooks in a single ``Request`` construction.

**How to apply:** Modify ``requests/models.py`` in the ``Request.__init__`` method to detect when a hook value is a list (or tuple) and, if so, iterate over each callable when invoking the hook. Ensure backward compatibility by still accepting a single callable. Update any related documentation and add tests for registering multiple hooks.
