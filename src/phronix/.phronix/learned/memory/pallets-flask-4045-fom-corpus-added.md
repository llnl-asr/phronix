---
name: pallets-flask-4045-fom-corpus-added
description: Added figure of merit and instance corpus for pallets__flask-4045 research
metadata:
  type: project
---

The research for the topic `pallets__flask-4045` now includes a defined figure of merit `target-test-failures` (minimize failing target tests) and a corpus of 8 instances covering dimensions `blueprint_name` (valid/invalid) and `endpoint_name` (valid/invalid). The instances have been added and split into train, validate, and test sets.

**Why:** The plan required a metric and a sufficient corpus to evaluate approaches.

**How to apply:** Subsequent research steps can use `research_define_fom` results and the created instances (see `research_status`) to measure approach performance and select the best approach.
