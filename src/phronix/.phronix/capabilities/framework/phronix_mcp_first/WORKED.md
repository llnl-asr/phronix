# What worked: phronix_mcp_first

- [tool:phronix_mcp_first_plan] 2026-11-13: `phronix_mcp_first_plan(goal, facts)` renders the 7-step checklist of mcp-first; facts cannot_repair_in_budget, new_or_renamed_tool, workload_fact switch the conditional steps (verified by checks.json).
- [tool:phronix_mcp_first_check] 2026-11-13: a record with tool, error, outcome, fix, recalled, lesson, workaround_used, defect_report filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:session_configure] 2026-09-15: a build-tool detection gap ('Unsupported build tool: unknown') is fixed in the detector, not by driving pip by hand (mcp-first E1).
