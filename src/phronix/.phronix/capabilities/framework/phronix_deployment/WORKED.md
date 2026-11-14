# What worked: phronix_deployment

- [tool:phronix_deployment_plan] 2026-11-13: `phronix_deployment_plan(goal, facts)` renders the 7-step checklist of phronix-deployment; facts ci, long_session, stale switch the conditional steps (verified by checks.json).
- [tool:phronix_deployment_check] 2026-11-13: a record with project, deploy_result, conflicts_overwritten, committed_paths, port_source, collector_bounced, restart_intended filled as the procedure requires passes; an empty record is inconclusive (verified by checks.json).
- [tool:phronix_deploy] 2026-09-15: --check deliberately excludes the harness memory symlink (keyed on the absolute project path) so an up-to-date tree reports no drift (P2).
