# What worked: phronix_trial_reconcile

- [tool:phronix_trial_reconcile_plan] 2026-11-13: `phronix_trial_reconcile_plan(goal, facts)` renders the 12-step checklist of phronix-trial-reconcile; facts none_passed, one_passed, several_passed switch the conditional steps (verified by checks.json).
- [tool:phronix_trial_reconcile_check] 2026-11-13: a record with ranking_finding, passed, candidates, branch, shared_assumption, assumption_check, corner_cases, step_reached, links, outcome, cost, transfer, instructions filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
