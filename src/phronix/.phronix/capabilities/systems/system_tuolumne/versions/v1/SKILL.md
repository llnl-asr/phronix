---
name: system_tuolumne
description: Tuolumne (LLNL, AMD MI300A, Cray PE + Cray MPICH, flux, one Rabbit per 16-node chassis) and the systems of its family that share its software (hetchy) - runtime library path, Rabbit #DW requests and capacity, queues by purpose, chassis rules, and the failure modes met running there. Load before planning, submitting or debugging any job on Tuolumne.
---
Cross-references: [[software_flux]] [[system_hetchy]] [[ropt_alloc]] [[workload_ipic3d]] [[rabbit-system-tuolumne]] [[rabbit-fs-xfs]] [[rabbit-fs-gfs2]] [[rabbit-fs-rabbit-lustre]] [[tools_parallel]]

## Rules
- Compiled Cray-MPICH apps run with `tuolumne_runtime_env([...app lib dirs])` on LD_LIBRARY_PATH, also inside flux batch jobs (flux copies the SUBMITTING environment).
- Every planned job goes through `tuolumne_check_job` before submission; every #DW capacity comes from `tuolumne_dw_capacity`.
- Queues by purpose: corpus evidence runs on `pbatch`; developer reproducers, fix validations and smoke tests on `pdebug`. Use the user's default flux bank unless they name one for that run.
- Rabbit jobs: one top-level `flux batch`/`flux alloc` carries the #DW directives (`--setattr=dw=...`), `--exclusive`, `--coral2-chassis=ceil(nodes/16)`; flux operations through [[software_flux]].
- Global parallel filesystem: `/p/lustre5/$USER` (6 MDTs, 28 OSTs). Never write run output to the NFS project space (`$PROJECT_ROOT`, home).
- Nodes: 96 cores, 4 GPUs (MI300A APU), ~502 GB memory; use all cores per node for MPI runs.

## Constraints
- One Rabbit per chassis of 16 computes (72 Rabbits, ~30.7 TB each). xfs/raw are per node; gfs2 profile=shared is shared only within one chassis (<= 16 nodes, `--coral2-chassis=1`); sharing across chassis needs Rabbit Lustre.
- xfs profile=shared is READ-ONLY and needs `#DW copy_in`.
- Only the default Lustre profile exists on production systems: omit `profile=` for type=lustre.
- A #DW directive must be on the TOP-LEVEL allocation: attached to a nested `flux run` inside a plain allocation it fails with "dws_environment event not found".
- The mount env var is `DW_JOB_<name>` with '-' -> '_', case-sensitive.

## Corner cases
### `libmpi_cray.so.12: cannot open shared object file` (and flux still says COMPLETED)
The environment lacks the Cray PE runtime dirs (detached submitter with a bare PATH). Fix: `tuolumne_runtime_env`; check the app's own log, not the flux result. Note: hetchy has no /opt/cray/lib64 and many PAPI versions - the tool picks what exists. (confirmed 2026-10-21, 2026-11-04)
### `DFTRACER_ENABLE: No such file or directory`, signal 127
`flux run -x DFTRACER_ENABLE ...`: -x is --exclusive, so the name became the command. Fix: `--env=DFTRACER_ENABLE`. (confirmed 2026-10-13)
### `dws_environment event not found` / `Error reading DW environment from eventlog`
#DW attached to a nested job inside a plain allocation. Fix: put the directives on the top-level batch/alloc. (confirmed 2026-10-13)
### Multi-node shared gfs2 hangs until timeout or ends in "node failure"
The allocation spanned chassis. Fix: <= 16 nodes with `--coral2-chassis=1`. (confirmed 2026-10-20)
### `Access denied to file` from H5FDmpio MPI_File_open on Rabbit Lustre at 4-8 nodes
Two bugs: capacity too small for the iterations, and `${DW_JOB_BENCH}` used for name=bench (empty -> writes to /). Fix: `tuolumne_dw_capacity(..., copies=iterations)` and the exact-case env var. (confirmed 2026-10-13)
### `DWS/Rabbit interactions failed: ... could not allocate storage`
One directive cannot be allocated and the whole job fails or hangs in setup; find which with `ropt_alloc_probe_storage` (on hetchy, Rabbit lustre on 2026-11-04). (confirmed 2026-11-04)
### Rabbit setup failure within seconds, or `alloc_denied (match error)`
Setup: retry, avoid nodes behind the failing rabbit (`flux job attach --read-only <id>`). match error: a nested run asked for more nodes than its allocation - size the allocation for the largest step.
### `--requires=-badrabbit`
Not needed: the submit plugin adds `not badrabbit` to every job. (confirmed 2026-10-21)

## Parallel plan
Builds on [[tools_parallel]]. Plan first (what must be found out, what must be done, what depends on what; `parallel_plan` for multi-step work), then:
- Validators (`tuolumne_check_job`) for different stages/items run together in one message.
- Acting calls (`tuolumne_runtime_env`, `tuolumne_dw_capacity`): independent items (different files, classes, traces, runs) go out together in one message, as one `parallel_call`, or as one sub-agent each; sequential only when a call needs an earlier result, a user gate/approval, or touches the same file/allocation/stage.
- While a long call (build, job, analysis) runs, prepare the next step in parallel instead of waiting idle.

## Corrector
Predictors: `tuolumne_runtime_env`, `tuolumne_dw_capacity`. Validator: `tuolumne_check_job` - each fault comes with its fix; change the plan, then check again.

## Self-heal
- A queue, limit or path differs from this skill: trust the live probe (`flux_queues`), then correct this skill with capability_update.
- A new runtime library error: add the directory through `extra_dirs_json`; if every app needs it, extend `runtime_dirs` with capability_update.

## Self-learn
- Anything new explored on Tuolumne (a queue rule, a Rabbit limit, an error and its fix) becomes a capability: the system fact here via capability_update (error -> cause -> fix -> verify, dated); app-specific findings in its workload_<app>; one-off notes in LESSONS.md.
