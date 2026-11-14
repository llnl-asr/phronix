# What worked: phronix_complexity

- [tool:phronix_complexity_plan] 2026-11-13: `phronix_complexity_plan(goal, facts)` renders the 6-step checklist of phronix-complexity; facts drift_down, drift_up, intrinsic_hard, store_changed switch the conditional steps (verified by checks.json).
- [tool:phronix_complexity_check] 2026-11-13: a record with subject, measured_level, drivers, declared_level, intrinsic, drift, action, model_id filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:complexity_assess] 2026-09-15: a drift down after work became capabilities is claimed by lowering model_level (R5).
