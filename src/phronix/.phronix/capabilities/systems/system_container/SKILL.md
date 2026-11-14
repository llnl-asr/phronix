---
name: system_container
description: System profile for Docker/Podman container environments: detected by /.dockerenv or a container* hostname (or user selection); no HPC module system, package-manager installs (apt-get / yum), MPI launched with plain `mpirun -n <N>` if present (check `which mpirun`), session temp under workspaces/<session>/tmp/. Load when system_detect reports `container`, on 'module: command not found', when srun/flux are absent, or when deciding whether sudo / package installs are allowed.
---
Cross-references: [[system_detect]] [[software_mpi]] [[software_pip]] [[tools_dftracer]] [[capability_builder]]

# system_container

Converted from dftracer-agents skill `system-container`. Tools: `system_container_recipe` (predictor) and `system_container_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- No HPC module system: use the system package manager (apt-get on Debian/Ubuntu, yum on RHEL/Rocky), direct paths, or virtualenvs.
- MPI may or may not be pre-installed: check `which mpirun` first; launch with `mpirun -n <N>` directly (no srun/flux).
- Session temp files go under workspaces/<session>/tmp/; /tmp is acceptable only for truly ephemeral scratch (the container resets on restart).
- sudo is available in the container but use it only for package-manager installs (`sudo apt-get install -y <pkg>` / `sudo yum install -y <pkg>`); the agent permission fence still says never sudo outside that and never write outside the project root.
- Run Bash (module, mpirun) only inside the active session workspace (cwd=workspaces/<session>/...), never the project root; write only workspaces/<session>/*.

## Constraints
- The source skill is internally inconsistent: 'Key Characteristics' says sudo is permitted, its 'Permissions' section says 'Never sudo'. The capability keeps sudo restricted to package installs; a host-level policy forbidding sudo wins.
- The source's Permissions line lists `module` among allowed commands although the container has no module system; treat module as unavailable.

## Corner cases
### `module: command not found`
Containers have no Lmod/Environment Modules. Install via apt-get/yum or use a virtualenv / direct paths.

### `mpirun: command not found`
MPI is not pre-installed in every image. Check `which mpirun`; install e.g. `sudo apt-get install -y openmpi-bin libopenmpi-dev` (Debian) or the yum equivalent.

### Files under /tmp vanished
The container reset on restart; keep anything that must persist under workspaces/<session>/tmp/.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `system_container_recipe` renders the recipe; validator `system_container_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_module_system` fails: Install with apt-get/yum or use a virtualenv / direct paths. Then render with `system_container_recipe` and validate again.
- `mpirun_launcher` fails: Use mpirun -n <N> <cmd>. Then render with `system_container_recipe` and validate again.
- `mpirun_checked` fails: Check which mpirun (install via package manager if missing) before launching. Then render with `system_container_recipe` and validate again.
- `sudo_only_for_packages` fails: Drop sudo, or restrict it to apt-get/yum install. Then render with `system_container_recipe` and validate again.
- `noninteractive_install` fails: Pass -y. Then render with `system_container_recipe` and validate again.

## Self-heal
- If detection disagrees (no /.dockerenv, hostname not container*), ask the user to confirm the system rather than assuming container.

## Self-learn
- Record per-image facts (base distro, preinstalled MPI, package names) here with a date.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this system goes into system_container via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) `which mpirun` -> install MPI with the package manager if absent -> `mpirun -n <N> <app>` from the session workspace.

## Source: dftracer-agents `system-container` (verbatim, headings demoted)
_Original description:_ System profile for Docker/Podman container environments — sudo available, no HPC module system, package-manager installs, MPI via mpirun

### System: Container

Docker/Podman container environment. Sudo is available.

#### Key Characteristics
- Root or sudo access is permitted in this environment.
- No HPC module system — use system package manager (`apt`, `yum`, etc.) as needed.
- MPI may or may not be pre-installed; check with `which mpirun`.

#### Temp / Workspace
- Use `workspaces/<session>/tmp/` inside the project directory for session-related temp files.
- `/tmp` is acceptable for truly ephemeral scratch (container resets on restart anyway).

#### Package Installation
```bash
# Debian/Ubuntu containers
sudo apt-get install -y <package>

# RHEL/Rocky containers
sudo yum install -y <package>
```

#### Detection
This system is active if:
- `/.dockerenv` exists, OR
- `hostname` returns `container*`, OR
- The user explicitly selects it.

#### Notes
- sudo is permitted here (unlike HPC systems).
- No module system; use direct paths or virtualenvs.
- MPI launch: use `mpirun -n <N>` directly.

#### Permissions

This skill uses:

- **Bash:** `module`, `mpirun` — run only inside the active session workspace (`cwd=workspaces/<session>/...`), never the project root
- **Write:** `workspaces/<session>/*` only

Never `sudo`; never write outside the project root.
