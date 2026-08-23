---
name: napoleon-use-param-other-parameters
description: napoleon_use_param now affects the Other Parameters section
metadata:
  type: feedback
---

Added conditional handling in `sphinx/ext/napoleon/docstring.py` to respect `napoleon_use_param` for the "Other Parameters" section, mirroring the Parameters section behavior. This includes using `self._consume_fields(multiple=True)` and `_format_docutils_params`. 

**Why:** The original code always formatted Other Parameters as fields, ignoring the config flag, leading to inconsistent documentation rendering.

**How to apply:** When customizing Napoleon parsing, ensure both Parameters and Other Parameters sections check `self._config.napoleon_use_param` and use the appropriate formatting functions.
