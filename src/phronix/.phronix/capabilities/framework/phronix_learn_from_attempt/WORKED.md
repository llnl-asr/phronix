# What worked: phronix_learn_from_attempt

- [tool:phronix_learn_from_attempt_plan] 2026-11-13: `phronix_learn_from_attempt_plan(goal, facts)` renders the 12-step checklist of phronix-learn-from-attempt; facts partial, passed, several_candidates, skill_exists switch the conditional steps (verified by checks.json).
- [tool:phronix_learn_from_attempt_check] 2026-11-13: a record with subject, verdict, evidence_read, solution_skill, fail_to_pass_passing, fail_to_pass_failing, entries, calls filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [django/auth-token/solution] 2026-09-15: use get_email_field_name() rather than user.email in the token hash; a custom user model has no email attribute (django__django-13551, 2 of 2).
