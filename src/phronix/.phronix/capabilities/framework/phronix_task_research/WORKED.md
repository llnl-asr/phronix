# What worked: phronix_task_research

- [tool:phronix_task_research_plan] 2026-11-13: `phronix_task_research_plan(goal, facts)` renders the 18-step checklist of phronix-task-research; facts budget_exhausted, needs_restructure, open_has_traceback switch the conditional steps (verified by checks.json).
- [tool:phronix_task_research_check] 2026-11-13: a record with problem, approaches, answer, open_failure, fix, must_keep_passing, lesson, retried_ruled_out, new_skill_created, research_validate_issues, layout_check_issues, solution_check_issues filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [django/custom-email-field/fix] 2026-09-15: get_email_field_name() instead of user.email; the naive form raises TypeError: must be str, not NoneType (phronix-task-research I4 example).
