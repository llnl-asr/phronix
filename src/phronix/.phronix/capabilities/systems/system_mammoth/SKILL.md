---
name: system_mammoth
description: Mammoth (mammoth34): Slurm scheduler, group-owned data paths, groups that change after login. Load on permission denied for a dataset or database, after a group change, or before choosing a launcher.
---
Cross-references: [[app_explore]], [[app_smoke]], [[moirai_run]], [[capability_builder]]

# system_mammoth

## Rules
- The scheduler is Slurm (pdebug 1 h, pbatch 24 h); the flux CLI exists but there is no broker, and moirai_run submits only through flux. A Slurm backend is a separate capability to build, never a workaround with ad-hoc sbatch.
- Probe data paths with mammoth_path_access (current groups, then sg per group), then mammoth_path_access_check.
- A group added after the shell and MCP server started is not in their process: readable only through sg means restart the session and MCP server; Slurm jobs normally get the current groups, confirm with a short probe job.
- Files owned by one user with mode 600 stay unreadable whatever the groups: ask the owner for chmod g+r, or readable copies.

## Constraints
- Read only; never chmod, copy or submit from here.

## Corner cases
- Rootless podman graphRoot defaults to HOME: redirect to the session or node-local /tmp.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- mammoth_path_access_check fails: if readable only through sg, restart the session and MCP server, then check again; if owner-only, ask the owner; the same failure twice stops the loop and goes to the user.

## Self-heal
- If a tool here is wrong, capability_update it; do not work around it in shell.

## Self-learn
- What is explored here becomes a capability: see capability_builder. Record each new mammoth fact (queues, banks, modules, groups) as a lesson here.
