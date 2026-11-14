# What worked: phronix_profiling

- [tool:phronix_profiling_plan] 2026-11-13: `phronix_profiling_plan(goal, facts)` renders the 7-step checklist of phronix-profiling; facts collector_down, parallel_steps switch the conditional steps (verified by checks.json).
- [tool:phronix_profiling_check] 2026-11-13: a record with run_id, env_exported_before_launch, steps, unattributed_fraction, events_dropped, parallel, parallel_noted, collector_restarted filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:profile_step_begin] 2026-09-15: same step id on every retry folds attempts together; model_level next to cost makes the level checkable (I3).
