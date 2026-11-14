# What worked: phronix_research_plan

- [tool:phronix_research_plan_plan] 2026-11-13: `phronix_research_plan_plan(goal, facts)` renders the 11-step checklist of phronix-research-plan; facts empty_diff, retry, scouts_active switch the conditional steps (verified by checks.json).
- [tool:phronix_research_plan_check] 2026-11-13: a record with summary, fom, axes, instances, split, prior_consulted, aspects, aspects_mode filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [pylint/research/plan] 2026-09-15: four steps with four different wheres; a wrong way at step 3 leaves steps 1, 2 and 4 standing (I5b).
