---
name: psf-requests-2148-research-metric-corpus
description: Added figure of merit and corpus instances for psf__requests-2148 research pass
metadata:
  type: project
---

We defined a figure of merit `fix_success_rate` (max, target 100%) with measure "percentage of tests passing after applying the approach". We declared a corpus with dimensions `input_type` (valid, invalid) and `module` (core, utils), target 8 instances. We added eight diverse instances covering all combos plus edge cases, and performed a train/validate/test split (5/1/2). This satisfies the required metric and corpus for subsequent research stages.

**Why:** The research plan required a metric and at least eight instances before proceeding.
**How to apply:** Use `research_define_fom` to record the metric, `research_declare_corpus` and `research_add_instances` to set up the dataset, and `research_split` to create splits for training, validation, and testing.
