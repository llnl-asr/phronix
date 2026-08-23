---
name: astropy-rst-header-rows-support
description: ascii.rst writer does not support header_rows keyword
metadata:
  type: project
---

The current Astropy ascii.rst writer raises an error when `header_rows` is provided, as demonstrated in issue # (see issue.md). This missing feature prevents users from adding custom header rows in restructured text output.

**Why:** Supporting `header_rows` aligns ascii.rst with other writer formats (fixed_width, etc.) and fulfills user request for header customization.

**How to apply:** Implement handling of `header_rows` in `astropy/io/ascii/rst.py` by extending the writer to process the list of header rows similar to other formats, updating documentation and tests accordingly.

[[astropy-rst-header-rows-support]]
