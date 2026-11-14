---
name: system_detect
description: Detect the current HPC/container system with mcp__dftracer__system_detect (hostname with trailing digits stripped -> resources/systems.yaml lookup returning module load order, env vars, MPI launcher, notes) and route to its system_<name> capability, or register a new system with mcp__dftracer__system_save. Load at the start of any dftracer session, when the system is unknown, when system_detect returns 'not in systems.yaml', or at session close to persist newly learned system nuances.
---
Cross-references: [[system_tuolumne]] [[system_tioga]] [[system_matrix]] [[system_dane]] [[system_container]] [[dftracer_system]] [[dftracer_session]] [[capability_builder]]

# system_detect

Converted from dftracer-agents skill `system-detect`. Tools: `system_detect_recipe` (predictor) and `system_detect_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Call mcp__dftracer__system_detect() first; it strips trailing digits from the hostname (tuolumne<node> -> tuolumne) and looks the base up in resources/systems.yaml.
- Recognised: confirm to the user which system was detected and summarise modules, MPI launcher and sudo availability.
- Not recognised ('not in systems.yaml'): offer tuolumne (AMD MI300A APU, Cray PE, no sudo), container (Docker/Podman, sudo available) or other (register a new system).
- For other/new: ask for the system name (hostname base, no digits) and needed modules/compilers/env vars, then mcp__dftracer__system_save(...) and confirm it was saved to resources/systems.yaml.
- Always end by telling the user which system is active and whether sudo is permitted.
- At session close, if new system nuances were learned (pitfalls, workarounds, env vars), update with mcp__dftracer__system_save(name="<system>", notes="<updated notes>", ...).

## Constraints
- Read-only probe: MCP system_detect / system_list / system_save; Bash only `module list` / `module avail`; no builds, no app execution, no source or workspace writes.
- Never sudo, never write outside the project root.

## Corner cases
### system_detect returns 'not in systems.yaml'
Unknown hostname base. Present tuolumne / container / other; for other collect name + modules + env and call system_save.

### Probe reports a GPU or power source that is not there (dane, matrix)
Detection keys on file existence (/opt/rocm-*, nvidia-smi). Trust the system capability's pins (e.g. tracing.power: off) over the probe; see system_dane / system_matrix.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `system_detect_recipe` renders the recipe; validator `system_detect_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `save_name_no_digits` fails: Use the base name (e.g. tuolumne, not tuolumne1001). Then render with `system_detect_recipe` and validate again.
- `detect_before_save` fails: Call mcp__dftracer__system_detect() first. Then render with `system_detect_recipe` and validate again.
- `module_read_only` fails: Use module list / module avail. Then render with `system_detect_recipe` and validate again.
- `no_build_or_run` fails: Hand off to the build/run stage after detection. Then render with `system_detect_recipe` and validate again.
- `no_sudo` fails: Drop sudo; detection needs none. Then render with `system_detect_recipe` and validate again.

## Self-heal
- If the detected system's config contradicts what the session observes, update it via system_save notes at session close rather than silently diverging.

## Self-learn
- Persist new system nuances via mcp__dftracer__system_save at session close.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this system goes into system_detect via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) system_detect -> confirm -> (unknown) ask + system_save -> report active system and sudo.

## Source: dftracer-agents `system-detect` (verbatim, headings demoted)
_Original description:_ Detect the current HPC/container system via mcp__dftracer__system_detect and load its module/env/MPI-launcher configuration, or register a new system

### System Detection

Detect the current HPC/container system and load appropriate configuration.

#### Steps

1. **Call the MCP tool** to auto-detect:
   ```
   mcp__dftracer__system_detect()
   ```
   This strips trailing digits from the hostname (e.g. `tuolumne<node>` → `tuolumne`),
   looks up the system in `resources/systems.yaml`, and returns the module load
   order, env vars, MPI launcher, and notes.

2. **If the system is recognised**: confirm to the user which system was detected
   and summarise the key config (modules, MPI launcher, sudo availability).

3. **If the system is not recognised** (MCP tool returns "not in systems.yaml"):
   Present the user with these options:
   - `tuolumne` — AMD MI300A APU cluster, Cray PE environment, no sudo
   - `container` — Docker/Podman container, sudo available
   - `other` — new system; I'll collect details and register it

4. **If user selects `other`** or a new system:
   - Ask: "What is the system name (hostname base, no digits)?
     What modules/compilers/env vars are needed?"
   - Collect the information.
   - Call `mcp__dftracer__system_save` with the gathered details.
   - Confirm the system was saved to `resources/systems.yaml`.

5. **Always end by telling the user** which system is active and whether
   sudo is permitted.

#### Session close
If new system nuances were learned during the session (pitfalls, workarounds,
additional env vars), update the system config before finishing:
```
mcp__dftracer__system_save(name="<system>", notes="<updated notes>", ...)
```

#### Permissions

Read-only system probe. This skill uses:

- **MCP:** `mcp__dftracer__system_detect`, `mcp__dftracer__system_list`, `mcp__dftracer__system_save`
- **Bash:** `module` (list/avail only) — no builds, no app execution
- **Write:** none — detection only; never modifies source or workspace files

Outer fence (global `.claude/settings.json`) still applies: never `sudo`, never write outside the project root.
