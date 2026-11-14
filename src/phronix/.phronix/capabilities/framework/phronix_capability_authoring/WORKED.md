# What worked: phronix_capability_authoring

- [tool:phronix_capability_authoring_plan] 2026-11-13: `phronix_capability_authoring_plan(goal, facts)` renders the 8-step checklist of phronix-capability-authoring; facts judgement_needed, running_server switch the conditional steps (verified by checks.json).
- [tool:phronix_capability_authoring_check] 2026-11-13: a record with name, byte_identical, overlapping_tools, docstring, error_examples, hardcoded_paths, judgement_calls, single_command_wrapper, layer, layer_reason, restart_stated, verifier, silent_defaults filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:capability_new] 2026-09-15: compiles the module and checks register before saving, so a broken tool is rejected at proposal time (I4).
