---
name: sympy-24066-fom
description: Define figure of merit for evaluating fixes to SI._collect_factor_and_dimension bug
metadata:
  type: project
---

**Why:**
A clear metric is needed to objectively compare candidate fixes for the dimensionless exponent bug. Without a quantitative figure of merit, research cannot determine which approach yields a correct and performant solution.

**How to apply:**
- The figure of merit should be the number of failing hidden tests that the fix resolves, minus any newly introduced failures, measured after running the full test suite.
- The metric must be collected by running the benchmark's hidden test suite (provided by the evaluation harness) and extracting the pass/fail count.
- A higher score indicates a better fix; the target is to achieve a score of zero failing hidden tests.

[[sympy-24066-corpus]]
