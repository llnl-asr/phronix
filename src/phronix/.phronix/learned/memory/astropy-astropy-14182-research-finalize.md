---
name: astropy-astropy-14182-research-finalize
description: Finalize research record for astropy-14182 task
metadata:
  type: project
---

This record marks the completion of the research stage for the task **astropy__astropy-14182**. The research skill `astropy-astropy-14182` indicates that the figure of merit is **header_rows-support** (target 100). The current status is:

- No source files were changed in this attempt (potential).
- The open issue remains to add support for `header_rows` in the RestructuredText writer.

**Why:** The attempt did not modify any files, and the verifier (hidden tests) still reports failure when `header_rows` is passed to `ascii.write(..., format="ascii.rst")`. Therefore the research remains open and the approach is still potential.

**How to apply:** Future work should implement handling of the `header_rows` keyword in `astropy/io/ascii/rst.py` (the `RST` writer). Once the implementation is added, the figure of merit can be measured by the number of hidden target tests passing.

**References:**
- Skill `astropy-astropy-14182` (`X1` block) outlines the open items.
- Issue description `issue.md` provides the failing traceback.

**Next steps:** Implement `header_rows` support in the RST writer, run hidden tests, and update this record with the result.
