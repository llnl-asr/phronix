# What worked: phronix_diagnosis_pivot

- [tool:phronix_diagnosis_pivot_plan] 2026-11-13: `phronix_diagnosis_pivot_plan(goal, facts)` renders the 6-step checklist of phronix-diagnosis-pivot; facts edits_not_run switch the conditional steps (verified by checks.json).
- [tool:phronix_diagnosis_pivot_check] 2026-11-13: a record with failure, assumption, edits_run, wanted, produced, new_path, differs_because, same_edit filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
