# What worked: phronix_agent_authoring

- [tool:phronix_agent_authoring_plan] 2026-11-13: `phronix_agent_authoring_plan(goal, facts)` renders the 8-step checklist of phronix-agent-authoring; facts behaviour_change, overrides_bundled, shared_rule switch the conditional steps (verified by checks.json).
- [tool:phronix_agent_authoring_check] 2026-11-13: a record with name, file_stem, description, model_level, tools, skills, missing_skills, edited_rendered_files, behaviour_change, user_confirmed, synced filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:agents_sync] 2026-09-15: re-renders every harness copy (.claude, .opencode, .github, .codex) from the template; then the user reloads the harness (I4).
