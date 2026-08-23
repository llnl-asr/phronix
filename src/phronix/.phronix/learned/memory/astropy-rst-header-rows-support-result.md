---
name: astropy-rst-header-rows-support-result
description: Result of research on ascii.rst writer header_rows support
metadata:
  type: project
---

The investigation confirmed that the Astropy `ascii.rst` writer raises a `TypeError` when the `header_rows` argument is supplied, as shown in the issue description. This missing feature prevents users from adding custom header rows in restructured text output, which is needed for the requested functionality.

**Why:** Supporting `header_rows` aligns `ascii.rst` with other writer formats (e.g., `fixed_width`) and fulfills a user request for richer RST output.

**How to apply:** Implement handling of the `header_rows` keyword in `astropy/io/ascii/rst.py`. Extend the writer to accept a list of header rows and prepend them to the output, similar to the implementation in other writers. Update documentation and add tests for the new feature.

The research stage is now complete; the next step is to create a development task to implement the feature and add appropriate tests.
