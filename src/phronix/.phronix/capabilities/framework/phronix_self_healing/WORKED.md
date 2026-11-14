# What worked: phronix_self_healing

- [tool:phronix_self_healing_plan] 2026-11-13: `phronix_self_healing_plan(goal, facts)` renders the 8-step checklist of phronix-self-healing; facts needs_restart, repeated_repair switch the conditional steps (verified by checks.json).
- [tool:phronix_self_healing_check] 2026-11-13: a record with symptom, status_checked, cause, repair, verified_diagnosis, edited_files, manual_workaround, class_fix, proof, lesson filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
