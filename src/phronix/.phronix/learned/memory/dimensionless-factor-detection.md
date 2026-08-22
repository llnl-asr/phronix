---
name: dimensionless-factor-detection
description: Detected that dimensionless exponent handling in SI._collect_factor_and_dimension needed proper exponent checking
metadata:
  type: project
---

Found that the current implementation of `SI._collect_factor_and_dimension` correctly handles dimensionless exponents by checking `self.get_dimension_system().is_dimensionless(exp_dim)` before applying exponent rules. No change needed for this part; the issue lies elsewhere in the exponent handling logic.

**Why:** The original hypothesis that dimensionless detection was flawed was disproven; tests for dimensionless cases pass.

**How to apply:** Focus future investigations on other parts of exponent handling, such as ensuring correct scaling of factor when exponent is dimensionless.
