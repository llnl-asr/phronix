# What worked: phronix_skill_authoring

- [tool:phronix_skill_authoring_plan] 2026-11-13: `phronix_skill_authoring_plan(goal, facts)` renders the 10-step checklist of phronix-skill-authoring; facts existing_subject, outgrown, pair_of_subjects, solves_problem switch the conditional steps (verified by checks.json).
- [tool:phronix_skill_authoring_check] 2026-11-13: a record with name, subject, description, instructions, labels_defined, labels_cited, solves_problem, failure_modes, contains_lessons, index_hand_written filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [pallets__flask-4045/solution/skill] 2026-09-15: raise ValueError (not assert) for dotted names in Blueprint.__init__ and both add_url_rule sites (endpoint, view_func.__name__); all three sites are needed.
