---
name: flask-blueprint-name-dot-validation
description: Blueprint names containing a dot should raise an error; also note test suite blocked by DeprecationWarning config
metadata:
  type: lesson
---

Lesson: Blueprint names containing a dot should raise an error. The test suite is blocked by DeprecationWarning config that treats warnings as errors. This can be resolved by adjusting filterwarnings in setup.cfg.
