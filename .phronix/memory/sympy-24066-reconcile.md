---
name: sympy-24066-reconcile
description: Reconcile attempt notes for sympy issue 24066: failed target test and missing research artifacts
metadata:
  type: project
---

## Why this reconciliation is needed
The recent attempt to fix `SI._collect_factor_and_dimension` in Sympy (issue 24066) still fails the hidden target test `test_issue_24062`. The failure shows that the change did not address the core bug: the `exp` of a dimensionful expression is not recognized as dimensionless. The existing research on degree padding (skill `degree-padding`) is unrelated; the current issue concerns dimension handling in the SI unit system.

## What was insufficient
- The attempted fix targeted the `max(powers.values())` filter in `itermonomials`, which does not affect the SI dimension computation.
- No changes were made to `sympy/physics/units/unitsystem.py` where `_collect_factor_and_dimension` lives.
- No figure of merit or corpus was defined for this research topic, as required by the workflow.

## Next steps (action items)
1. **Define a figure of merit** for the dimension‑handling bug, e.g. `dimension_handling_correctness_rate` (target 1.0), measured by running the hidden tests that check dimensionless detection.
2. **Create a research corpus** with instances covering various unit expressions, including exponentials, products, and nested units. At least 8 instances are needed.
3. **Add a new research approach** focusing on fixing `_collect_factor_and_dimension` (e.g., replace the `exp` handling to strip dimensions before processing).
4. **Record observations** using `research_observe` to capture what was tried and why it failed.

These actions will bring the research topic into a complete state, allowing the next attempt to make measurable progress.

## How to apply
- Use `research_define_fom` to record the metric.
- Use `research_declare_corpus` and `research_add_instances` to populate instances.
- Propose a new approach via `research_add_approach` with a clear hypothesis.
- Observe the failure with `research_observe(topic="sympy__sympy-24066", what="exp dimension handling", worked=false, detail="hidden test still fails after itermonomials fix")`.

**Linked memories**: [[degree-padding]] (unrelated but part of the same repository), [[sympy-24066-research-plan]] (to be created).
