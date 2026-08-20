---
name: pylint-7080-research-plan-written
description: Research plan written for pylint-7080 (--recursive=y ignores ignore-paths)
metadata:
  type: project
---

## Context
Task pylint-dev__pylint-7080: fixing bug where `--recursive=y` flag causes pylint to ignore the `ignore-paths` configuration from pyproject.toml.

## Finding
`research_assess` returned verdict "covered" - the skill library already contains `ignore-normalize-paths` with:
- Figure of merit defined (target_tests_passing)
- Dataset dimensions declared (config_location, ignore_pattern_type, recursive_flag)
- Two potential approaches documented
- Official fix PR identified: https://github.com/pylint-dev/pylint/pull/7080

## Why this matters
When `research_assess` says "covered", it means DO NOT re-research from scratch. The investigation has already been done. Load the skill and follow the documented approaches.

## What was done
Created structured research plan document at `tmp/research/opencode/RESEARCH_PLAN.md` containing:
1. **The metric**: target_tests_passing (fraction 0-1, measured by hidden tests + manual validation)
2. **The dataset**: 8 instances across 3 dimensions (config_location, ignore_pattern_type, recursive_flag)
3. **The aspects**: 3 independent investigation angles (path normalization, config loading, pattern matching)

## How to apply
When asked to "write the research plan" for a task:
1. Run `research_assess` FIRST to check if already covered
2. If "covered", synthesize the existing research into a structured plan document
3. If "gap", follow the research playbook to investigate from scratch
4. Document: metric → dataset → aspects (in that order)
5. Write to `tmp/research/opencode/` directory

The gate-first check prevents redundant research and ensures we build on prior work.
