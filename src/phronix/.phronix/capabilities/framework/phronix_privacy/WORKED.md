# What worked: phronix_privacy

- [tool:phronix_privacy_plan] 2026-11-13: `phronix_privacy_plan(goal, facts)` renders the 7-step checklist of phronix-privacy; facts new_leak_class, path_rule, scan_dirty switch the conditional steps (verified by checks.json).
- [tool:phronix_privacy_check] 2026-11-13: a record with target, scan_before, redacted, scan_after, suspects_run, dismissed, patterns_added, patched_files_by_hand, text filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:privacy_scan] 2026-09-15: the deterministic check before any commit/PR/promotion; reading the file is not a check (R4).
