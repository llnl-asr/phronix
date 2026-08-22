---
name: pylint-dev-7080-aspects-set
description: Set research aspects for pylint ignore-paths issue
metadata:
  type: project
---

We defined four research aspects for the pylint ignore-paths handling issue:
- ignore-paths handling: How does pylint process ignore-paths when --recursive=y is used?
- configuration loading: From where does pylint read the pyproject.toml settings in recursive mode?
- test case identification: Which test currently fails and what output does it produce?
- minimal reproducer: What is the smallest source tree that reproduces the ignore-paths issue?

**Why:** To structure the investigation and ensure all relevant questions are addressed.
**How to apply:** Use these aspects to guide subsequent probing and debugging steps.
