---
name: software_rocm
description: ROCm / HIP / rocprofiler-sdk knowledge for dftracer HIP tracing on AMD GPUs (MI300A): the strict init ordering rocprofiler_force_configure needs (import torch before initialize_log, before touching the GPU), building DFTRACER_ENABLE_HIP_TRACING against a ROCm >= 6.2 prefix on CMAKE_PREFIX_PATH (else it silently compiles out), PyTorch-profiler coexistence for exactly one profiler window, ROCm base-vs-patched tree matching with the torch wheel, MI300A unified-memory scope, XLA preallocation on APUs, RCCL transport (rccl/working-env, aws-ofi-rccl on LD_LIBRARY_PATH, never guess NCCL_NET), the DDP fork-bomb on non-exclusive flux run, and the HIP-tracing observer effect. Load for any DFTRACER_ENABLE_HIP_TRACING session or ROCm/HIP/RCCL build or run issue, or on: 'Error Calling hsa_iterate_agents: HSA_STATUS_ERROR_NOT_INITIALIZED', "Check failed: '_v' Must be non nullptr", zero HIP_RUNTIME_API/KERNEL_DISPATCH events, 'Memory access fault by GPU node-N ... Reason: Unknown', RCCL hangs or slow host-TCP collectives, Ray TrainingFailedError at a profiler cycle boundary.
---
Cross-references: [[software_cupti]] [[software_mpi]] [[software_papi]] [[software_molformer]] [[software_ray]] [[software_flux]] [[system_tuolumne]] [[tools_dftracer]] [[tools_pydftracer]] [[dftracer_install]] [[workload_scaffold]] [[workload_rajaperf]] [[capability_builder]]

# software_rocm

Converted from dftracer-agents skill `software-rocm`. Tools: `software_rocm_recipe` (predictor) and `software_rocm_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- HIP tracing init window: dftracer (DFTRACER_ENABLE_HIP_TRACING=ON) calls rocprofiler_force_configure() from HIPFunction::initialize() inside dftracer.initialize_log(); rocprofiler-sdk accepts it only AFTER the HSA/HIP shared libraries are loaded and BEFORE hsa_init() ran. So: `import torch` (module load only) -> initialize_log() -> first GPU touch, in every GPU process.
- For frameworks that initialize dftracer at an entry point you do not own (e.g. Ray default_worker.py), import torch from a sitecustomize.py on PYTHONPATH gated on DFTRACER_ENABLE == "1"; no edits under site-packages.
- DFTRACER_ENABLE_HIP_TRACING is compile-time only; there is no runtime switch to turn HIP tracing off once built in.
- Build against a ROCm >= 6.2 prefix with the ROCm prefix APPENDED to CMAKE_PREFIX_PATH (HDF5's prefix may already be there) and ROCM_PATH/HIP_PATH set, or find_package(rocprofiler-sdk) fails and HIP tracing silently compiles out.
- After a HIP-tracing install, never trust exit 0: verify on a real GPU run that HIP_RUNTIME_API / KERNEL_DISPATCH categories are non-empty; HIP-enabled smoke tests must check those categories.
- PyTorch profiler via pydftracer `dftracer.python.torch.trace_handler` (on_trace_ready): record_shapes=True REQUIRED, profile_memory=True feeds cpu_memory/device_memory_usage, with_stack OFF, ProfilerActivity.CUDA is correct on ROCm, stop the profiler BEFORE dftracer.finalize() (else last window's PP events are dropped).
- With HIP tracing + torch profiler use repeat=1 (one active window per process); widen active= rather than adding cycles. A repeating short cycle (wait=0, warmup=0, active=K, repeat=0) is UNTESTED against the second-cycle abort.
- dftracer and the torch +rocm wheel must be built against the SAME ROCm tree (base vs patched hangfix/leakfix/cgroupfix). Prefer patched only when nothing else constrains it; check whether a patched variant even exists (rocm/7.1.1 on Tuolumne has none, torch pinned +rocm710).
- MI300A unified memory is INTRA-PACKAGE only: data moved between APUs on a node crosses Infinity Fabric. Never justify multi-APU sharding with 'unified memory makes it free'; independent units of work per APU cost ~0 communication.
- Unified PHYSICAL memory != any host pointer is GPU-addressable: the GPU addresses only HIP-registered ranges (hipMalloc, hipMallocManaged, hipHostMalloc, hipHostRegister). hipMemAdvise only hints. Use hipMallocManaged for zero-staging-copy APU behaviour.
- On MI300A APUs always test XLA_PYTHON_CLIENT_PREALLOCATE=false explicitly (preallocated pool comes out of the same HBM the CPU side uses). XLA_PYTHON_CLIENT_MEM_FRACTION is an unmeasured secondary candidate.
- Multi-node RCCL needs rccl/working-env (or the site equivalent); its FI_MR_CACHE_MONITOR=userfaultfd is load-bearing. Without it jobs hang instead of erroring.
- Put the site libfabric plugin (aws-ofi-rccl) lib dir on LD_LIBRARY_PATH, else RCCL silently falls back to host TCP (40%+ wall time). Leave NCCL_NET UNSET; a guessed name (NCCL_NET=libfabric vs the plugin's 'AWS Libfabric') is a hard failure that looks like an ABI issue.
- A gloo vs nccl/rccl A/B is invalid if both fell back to host TCP: verify the actual transport in use before concluding.
- Node-local multi-GPU DDP via flux run: always --exclusive, and `unset PMI_RANK PMI_SIZE PMI_FD PALS_APID PALS_APINFO PALS_NODEID PALS_RANKID PALS_SPOOL_DIR LDCS_RANKINFO` before the training process (full recipe in software_flux).
- Size GPU launch-overhead optimizations against UNTRACED app timings: HIP tracing inflates launch/sync-heavy kernels 6-7x (cost proportional to call count). Keep tracing state identical across optimization arms, but size bottlenecks untraced.

## Constraints
- rocm-smi --setperflevel is admin-gated on LC systems (no sudo); MI300A already boosts under load: treat as not tunable.
- HSA_ENABLE_INTERRUPT=0 regresses mixed CPU+GPU apps; only consider for a pure-GPU sync-heavy phase with idle host cores.
- MIOpen find-mode / vendor conv auto-tune is not applicable to apps that emit their own HIP kernels.
- NUMA/CPU-GPU affinity binding is a confirmed no-op on the MI300A system across four workload classes: do not re-propose without a new mechanism.
- The XLA preallocation win was measured at small scale (~110 s job); verify at larger scale.

## Corner cases
### SIGABRT: `Error Calling hsa_iterate_agents: HSA_STATUS_ERROR_NOT_INITIALIZED` then `Check failed: '_v' Must be non nullptr`
Cause: initialize_log() ran before the HSA/HIP libraries were loaded (no torch imported; narrowing HIP_VISIBLE_DEVICES does not help). Fix: import torch (module load only) before initialize_log(). Verify: HIP_RUNTIME_API, KERNEL_DISPATCH, MEMORY_COPY, SCRATCH_MEMORY present. (MI300A, ROCm 6.2.4, rocprofiler-sdk 0.4.0, torch 2.6.0+rocm6.2.4)

### Trace healthy but ZERO HIP events (all other categories present)
Cause A: torch touched the GPU (or dftracer.dftracer imported first then GPU touched) before initialize_log(): force_configure silently locked. Fix: import torch -> initialize_log() -> touch GPU. Cause B: dftracer built without ROCm on CMAKE_PREFIX_PATH, so rocprofiler-sdk was not found and HIP tracing compiled out. Easy to misread as 'app does no GPU work'.

### Ray `TrainingFailedError` / worker `SYSTEM_ERROR` after N iterations with `Check failed: '_v' Must be non nullptr` far below the traceback
Cause: second torch-profiler cycle re-arms roctracer while dftracer's rocprofiler-sdk context is live (schedule repeat=2). Fix: repeat=1; widen active=.

### App aborts before training starts after building dftracer against rocm/<ver>hangfix
Cause: torch +rocm<ver> wheel built against the BASE tree; two rocprofiler/HIP runtimes mixed. Fix: rebuild dftracer against the same base ROCm tree the wheel targets.

### SIGABRT rc=134, repeated `Memory access fault by GPU node-4 ... Reason: Unknown` on the first kernel
Cause: plain aligned host malloc + hipMemAdvise (RAJAPerf --hip-data-space HipHostAdviseFine); the range was never HIP-registered. Fix: hipMallocManaged (or hipHostMalloc / hipHostRegister). (MI300A, ROCm 7.2.1, 2026-08-05)

### Multi-node RCCL collective hangs, no error
Cause: rccl/working-env module not loaded (FI_MR_CACHE_MONITOR=userfaultfd missing). Fix: module load rccl/working-env.

### Collective-heavy job 40%+ slower, no warnings
Cause: aws-ofi-rccl plugin not on LD_LIBRARY_PATH, RCCL fell back to host TCP sockets. Fix: add the plugin lib dir to LD_LIBRARY_PATH; leave NCCL_NET unset.

### RCCL/NCCL hard failure that looks like an ABI incompatibility after setting NCCL_NET
Cause: NCCL_NET set to a guessed provider (e.g. libfabric) not matching the plugin's registration name ('AWS Libfabric'). Fix: unset NCCL_NET.

### Node fork-bombed by DDP under `flux run`
Cause: Flux's PMI shim sets PMI_RANK=0/PMI_SIZE=1/PALS_*/LDCS_RANKINFO for any flux run; every DDP child inherits PMI_RANK=0 and re-spawns siblings, triggered when requesting more GPUs than a non-exclusive slice grants. Fix: --exclusive and unset the PMI/PALS vars. See software_flux.

### HIP_RUNTIME_API bucket implies ~43 us per HIP call; GPU variant looks 18x slower than serial
Cause: tracing observer effect proportional to call count (RAJAPerf MI300A ROCm 7.2.1: 0.960 s traced vs 0.144 s untraced p50, 6.1-6.7x). Fix: cross-check against untraced app timing before sizing.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_rocm_recipe` renders the recipe; validator `software_rocm_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `hip_tracing_needs_rocm_prefix` fails: export ROCM_PATH=<rocm-prefix>; export CMAKE_PREFIX_PATH=$ROCM_PATH:$CMAKE_PREFIX_PATH before the build. Then render with `software_rocm_recipe` and validate again.
- `no_nccl_net_guess` fails: Leave NCCL_NET unset; put the aws-ofi-rccl lib dir on LD_LIBRARY_PATH. Then render with `software_rocm_recipe` and validate again.
- `torch_profiler_single_window` fails: Use repeat=1 and widen active= for more coverage. Then render with `software_rocm_recipe` and validate again.
- `torch_profiler_record_shapes` fails: Pass record_shapes=True to torch.profiler.profile. Then render with `software_rocm_recipe` and validate again.
- `rccl_working_env` fails: module load rccl/working-env before launching. Then render with `software_rocm_recipe` and validate again.
- `rccl_plugin_on_ld_library_path` fails: export LD_LIBRARY_PATH=<aws-ofi-rccl>/lib:$LD_LIBRARY_PATH. Then render with `software_rocm_recipe` and validate again.
- `flux_ddp_exclusive` fails: Launch with flux run --exclusive and unset PMI_*/PALS_*/LDCS_RANKINFO first. Then render with `software_rocm_recipe` and validate again.
- `no_hsa_interrupt_off` fails: Drop HSA_ENABLE_INTERRUPT=0 unless the phase is pure-GPU with idle host cores. Then render with `software_rocm_recipe` and validate again.
- `no_rocm_smi_perflevel` fails: Remove it; treat GPU perf level as not tunable. Then render with `software_rocm_recipe` and validate again.
- A clean HIP-tracing build with zero HIP events: re-check the ROCm prefix on CMAKE_PREFIX_PATH at dftracer configure time before touching the app's import order.

## Self-heal
- Missing HIP events: check (1) rocprofiler-sdk found at dftracer configure (ROCm on CMAKE_PREFIX_PATH), (2) import order torch -> initialize_log -> GPU touch, (3) torch profiler repeat, (4) base-vs-patched ROCm agreement.
- Suspected slow collectives: confirm the actual RCCL transport (plugin resolvable on LD_LIBRARY_PATH) before comparing backends.

## Self-learn
- Record measured ROCm-version / torch-wheel / rocprofiler-sdk combinations and APU tuning results here with system, ROCm version and date; mark untested schedules as untested.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_rocm via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (MI300A, ROCm 6.2.4, rocprofiler-sdk 0.4.0, torch 2.6.0+rocm6.2.4) `import torch` (load only) -> `initialize_log()` -> touch GPU: HIP_RUNTIME_API, KERNEL_DISPATCH, MEMORY_COPY, SCRATCH_MEMORY all emitted.
- (MI300A, ROCm 6.2.4, Ray Train 8-GPU DDP) HIP tracing + kineto torch profiler with one window in the same process: HIP_RUNTIME_API 972k, KERNEL_DISPATCH 146k, POSIX 89k, STDIO 32k, dftracer 17k, PP 777, MEMORY_COPY 347, comm 260 per worker trace.
- (2026-08-02, MI300A AF3/JAX) XLA_PYTHON_CLIENT_PREALLOCATE=false: peak node memory 122.8 -> 28.4 GiB (-77%), wall -4.9%, ptm/iptm unchanged.
- (2026-08-05) Detection/install fix: ROCM_PATH/HIP_PATH set in dftracer_pip_env and ROCm prefix appended to CMAKE_PREFIX_PATH whenever HIP tracing is needed.

## Source: dftracer-agents `software-rocm` (verbatim, headings demoted)
_Original description:_ > Generic ROCm/HIP/rocprofiler-sdk knowledge for dftracer HIP tracing on AMD GPU systems (e.g. MI300A) — init-ordering requirements, coexistence with the PyTorch profiler, ROCm base-vs-patched tree matching, and RCCL transport selection. Load this skill for any dftracer session with DFTRACER_ENABLE_HIP_TRACING or any ROCm/HIP/RCCL build or run issue, not tied to one specific app.

Cross-references: [[dftracer-install]] [[software-mpi]] [[software-molformer]] [[workload-scaffold]]

---

#### HIP tracing (rocprofiler-sdk) requires a strict init ORDER, not just the right flags

`dftracer` built with `DFTRACER_ENABLE_HIP_TRACING=ON` calls
`rocprofiler_force_configure()` from `HIPFunction::initialize()`, which runs inside
`dftracer.initialize_log()`. rocprofiler-sdk tolerates that call in exactly ONE
window: after the HSA/HIP shared libraries are LOADED, but before `hsa_init()` has
run. Bisected on an MI300A compute node (ROCm 6.2.4, rocprofiler-sdk 0.4.0, torch
2.6.0+rocm6.2.4):

| case | ordering | result |
|---|---|---|
| A | `initialize_log()`, no torch imported at all | **SIGABRT**: `Error Calling hsa_iterate_agents: HSA_STATUS_ERROR_NOT_INITIALIZED` then `Check failed: '_v' Must be non nullptr` |
| B | same as A + narrow `HIP_VISIBLE_DEVICES` after init | same SIGABRT (not about visible-device masking) |
| C | `import torch` + touch GPU, THEN `initialize_log()` | no crash, but **zero HIP events** — force_configure is already locked, silently |
| D | `import dftracer.dftracer` first, then C | same silent no-op |
| E | `import torch` (module load only), THEN `initialize_log()`, THEN touch GPU | **works**: `HIP_RUNTIME_API`, `KERNEL_DISPATCH`, `MEMORY_COPY`, `SCRATCH_MEMORY` all emitted |

**Case C/D is the dangerous one** — it looks healthy and produces a trace with every
other category present, so a missing-HIP-events report is easy to misread as "this
app does no GPU work" rather than an init-ordering bug.

**How to apply:** ensure something imports torch (module load only is enough) BEFORE
the first `initialize_log()` in every process that will use a GPU, and before any
code touches the GPU. For frameworks that initialize dftracer at a process entry
point you do not own (e.g. Ray's `default_worker.py`), do it with a
`sitecustomize.py` on `PYTHONPATH` gated on `DFTRACER_ENABLE == "1"` — `site` imports
it at interpreter startup, before any script body, and it needs no edits under
`site-packages`.

Also: `DFTRACER_ENABLE_HIP_TRACING` is COMPILE-time only; there is no runtime env var
to turn HIP tracing off once the build has it. Build against a ROCm >= 6.2 prefix
with `CMAKE_PREFIX_PATH=$ROCM_PATH` or `find_package(rocprofiler-sdk)` fails and it
silently compiles out (no error, just no HIP tracing).

**Confirmed missing in `session_install_dftracer` itself (fixed 2026-08-05,
RAJAPerf session).** Detection correctly set `DFTRACER_ENABLE_HIP_TRACING=ON`
in `dftracer_pip_env`/`DFTRACER_CMAKE_ARGS` whenever `hip_tracing_needed` was
true, but never set `ROCM_PATH`/`HIP_PATH`/`CMAKE_PREFIX_PATH` alongside it —
so every HIP-tracing dftracer install up to this point would have hit exactly
the silent-compile-out failure mode this paragraph warns about (a build that
reports success, produces a working library, but with zero
`HIP_RUNTIME_API`/`KERNEL_DISPATCH` events ever possible — the kind of gap
that's easy to misread as "this app does no GPU work" per the case C/D
warning above, except one level earlier: dftracer itself never got the
capability compiled in). Fixed in two places: `detection.py`'s `_detect_info`
now sets `ROCM_PATH`/`HIP_PATH` in `dftracer_pip_env` from the resolved
`rocm_info["path"]` whenever `hip_tracing_needed`; `install.py`'s
`_install_dftracer_pip_direct` now also APPENDS the ROCm prefix to
`CMAKE_PREFIX_PATH` (not overwrite — HDF5's own prefix may already occupy
that var) when `features["hip"]` is set. After a HIP-tracing dftracer
install, don't just trust exit 0 — verify with a real GPU run that
`HIP_RUNTIME_API`/`KERNEL_DISPATCH` categories are actually non-empty in the
trace (this is also why the smoke-test step for any HIP-enabled session
should explicitly check for those categories, not just "did the binary run").

#### PyTorch profiler + dftracer HIP tracing coexist for exactly ONE profiler window

`pydftracer` (develop) ships `dftracer.python.torch.trace_handler`, which replays
every torch `FunctionEvent` into the dftracer log as `cat="PP"` events anchored on
kineto's `trace_start_ns`. Wire it as `torch.profiler.profile(...,
on_trace_ready=trace_handler)`.

Requirements that are easy to get wrong:
- `record_shapes=True` is REQUIRED — the handler derives its `input_size` arg from
  `event.input_shapes`.
- `profile_memory=True` feeds the `cpu_memory` / `device_memory_usage` args.
- `with_stack` should stay OFF: very expensive, and the handler never reads stacks.
- On ROCm, `ProfilerActivity.CUDA` is the correct enum (HIP is exposed through
  torch's `cuda` namespace).
- Stop the profiler BEFORE `dftracer.finalize()`, or the last active window's `PP`
  events are dropped — the handler writes through the dftracer logger.

**Measured co-existence result** (MI300A, ROCm 6.2.4, Ray Train 8-GPU DDP, dftracer
develop with HIP tracing ON): a single per-worker trace contained, simultaneously,
`HIP_RUNTIME_API` 972k, `KERNEL_DISPATCH` 146k, `POSIX` 89k, `STDIO` 32k, `dftracer`
17k, `PP` 777, `MEMORY_COPY` 347, `comm` 260 — so HIP tracing and the kineto-based
PyTorch profiler DO work together in the same process.

**But a SECOND profiler cycle re-arms roctracer and aborts.** With
`schedule(wait=2, warmup=1, active=5, repeat=2)` the run completed 7 training
iterations, then aborted at the SECOND profiler cycle boundary with the same
rocprofiler assertion as the init-ordering bug (`Check failed: '_v' Must be non
nullptr`). Tearing kineto's GPU collection down and re-arming it while dftracer's
rocprofiler-sdk context is live trips it. The failure is silent-looking from the app
side — e.g. Ray reports a generic `TrainingFailedError`/worker `SYSTEM_ERROR`, and
the abort line appears far below the Python traceback in the log.

**How to apply:** use `repeat=1` (one active profiler window per process) when HIP
tracing and the PyTorch profiler are both on. If more coverage is needed, widen
`active=` rather than adding cycles. If you need PP events spread across the whole
run rather than one end-of-run flush, use a REPEATING short cycle
(`schedule(wait=0, warmup=0, active=K, repeat=0)`, `repeat=0` = forever) so
`trace_handler` flushes every K steps — but this has NOT been validated against the
second-cycle-abort hazard above, so treat it as untested, not assumed safe, until a
session actually runs it to completion.

#### ROCm base-vs-patched tree: dftracer and the torch wheel must agree

Building dftracer against a *patched* `rocm/<ver>hangfix` (or `leakfix`/`cgroupfix`)
tree while torch is a `+rocm<ver>` wheel built against the BASE (unpatched) tree
mixes two rocprofiler/HIP runtimes and can abort the app before training even
starts. Rebuilding dftracer against the SAME base ROCm tree the torch wheel targets
lets training start and the profiler engage on all ranks. This is a real qualifier
on "prefer the patched module for its bug fixes" — prefer patched when nothing else
constrains it, but dftracer and the torch wheel must agree on which tree, patched or
base, they were both built against. Also confirmed: a ROCm version with NO patched
variant at all (e.g. `rocm/7.1.1` on Tuolumne, where the torch wheel is pinned to
`+rocm710`) sidesteps this entirely — check whether a patched variant even exists
before assuming one must be chosen.

#### MI300A "unified memory" is INTRA-PACKAGE only, not node-wide

An MI300A APU's zero-copy/unified-address property is that ONE package's CPU
cores and GPU XCDs share that package's own HBM stack — this is what removes
the host↔device copy penalty within a single APU. It does **NOT** mean data
movement is free BETWEEN the several APUs on one node: that traffic still
crosses Infinity Fabric and is a real bandwidth/latency-bounded transfer.
Confirmed reasoning (AF3/JAX session, 2026-08-02, evaluating a proposal to
shard one inference across 4 APUs): sharding a single unit of work across
APUs would introduce cross-package Infinity-Fabric exchanges on the critical
path where none exist today, plus RCCL/collective initialization cost and the
risk of collective time being mislabeled as compute in a trace with HIP
tracing off (it only shows up as `KERNEL_DISPATCH`/`ncclDevKern` when HIP
tracing is on). By contrast, running independent units of work (e.g.
independent inference seeds) across the 4 APUs — one per device, no
gradient, no collective — costs ~0 extra communication, because there is
nothing to synchronize. **Never justify a multi-APU model-sharding proposal
with "unified memory makes it free"** — check whether the proposed data
movement is intra-package (free) or inter-package (real cost) first. Refs:
Bertolli et al., SC24-W (zero-copy OpenMP on MI300A, per-package scope);
Kuncham, Zhang & Panda, IPDPS 2026, *One Memory–Many Paths* (allocation/copy
path taxonomy on MI300A).

#### `XLA_PYTHON_CLIENT_PREALLOCATE=false` is a real win on MI300A APUs, unlike on discrete GPUs

JAX's default behavior reserves ~75% of the visible device memory pool up
front (`XLA_PYTHON_CLIENT_PREALLOCATE` defaults to `true`). On a discrete GPU
this is a genuinely free reservation — it just claims device-only VRAM the
CPU side never touches. **On an MI300A APU it is not free**, because the
preallocated pool is carved out of the SAME unified HBM the CPU-side pipeline
(featurization, tokenization, any host-side numpy/RDKit work) allocates from.
Measured (AF3 inference, JAX/ROCm, 2026-08-02, small-structure probe, 3
replicates/side, disjoint ranges): setting `XLA_PYTHON_CLIENT_PREALLOCATE=false`
cut peak node memory from 122.8 GiB to 28.4 GiB (**-77%**) AND cut wall time
by **-4.9%**, with model output confidence metrics (`ptm`/`iptm`) unchanged.
Env-var only, zero source edits. **Always test this env var explicitly on
APU (unified-memory) systems** — the classic discrete-GPU tuning advice
("preallocation avoids fragmentation, always leave it on") does not transfer.
Caveat: measured at small scale only (~110s job); may dilute at a
GPU-inference-dominated scale where the pool-vs-CPU contention is a smaller
fraction of total memory pressure — verify before assuming it holds at every
scale. A secondary, unmeasured candidate in the same family:
`XLA_PYTHON_CLIENT_MEM_FRACTION` (a smaller explicit fraction instead of
`false`) may recover part of the win with less allocator churn.

#### RCCL transport selection

- `rccl/working-env` (or the site's equivalent RCCL environment module) is required,
  not optional, for multi-node RCCL collectives on ROCm — without it the job hangs
  instead of erroring. Its `FI_MR_CACHE_MONITOR=userfaultfd` setting is load-bearing;
  don't drop it when hand-rolling an environment instead of using the module.
- RCCL can silently fall back to slow host TCP sockets instead of the fast
  fabric-provider transport if the site's libfabric plugin (e.g. `aws-ofi-rccl`) is
  not on `LD_LIBRARY_PATH` — this can cost 40%+ of a collective-heavy workload's
  wall time with zero errors or warnings. Fix: add the plugin's lib dir to
  `LD_LIBRARY_PATH`. Do NOT set `NCCL_NET` to a guessed provider name (e.g.
  `NCCL_NET=libfabric`) as a "fix" — if it doesn't exactly match the plugin's own
  registration name (e.g. the AWS plugin registers as `AWS Libfabric`, not
  `libfabric`), NCCL/RCCL treats the mismatch as a hard failure that is easy to
  misdiagnose as an ABI incompatibility rather than a naming mismatch. Leave
  `NCCL_NET` UNSET and let RCCL auto-select once the plugin is actually resolvable
  on `LD_LIBRARY_PATH`.
- A same-system A/B between `gloo` and `nccl`/`rccl` backends is not a valid
  transport comparison if BOTH ended up on host TCP due to the plugin-path issue
  above — verify the actual transport in use (not just which backend name was
  requested) before drawing a conclusion from a backend comparison.

#### PyTorch/Lightning DDP fork-bomb on a non-`--exclusive` single-task `flux run`

Launching node-local multi-GPU DDP training via `flux run` without `--exclusive` can
silently fork-bomb the node — Flux's PMI shim sets `PMI_RANK=0`/`PMI_SIZE=1`/
`PALS_*`/`LDCS_RANKINFO` for ANY `flux run`, even a plain single-task non-MPI one,
and every spawned DDP child inherits the SAME `PMI_RANK=0` unchanged, so none of them
recognize themselves as an already-spawned child — each re-triggers spawning its
siblings, recursively, without bound. This is generic to any subprocess-based
multi-GPU launcher (PyTorch Lightning's `ddp` strategy, raw `torch.distributed`
subprocess launch), not ROCm-specific, but reliably shows up on ROCm/MI300A sessions
because the fork-bomb only actually fires once combined with a real error condition —
typically requesting more GPUs than a non-`--exclusive` job's fair-share slice
actually grants. See the `flux-alloc` skill's "PyTorch Lightning / torch.distributed
DDP on a non-`--exclusive` single-task `flux run` can fork-bomb the node" section for
the full fix (always launch with `--exclusive`, and `unset PMI_RANK PMI_SIZE PMI_FD
PALS_APID PALS_APINFO PALS_NODEID PALS_RANKID PALS_SPOOL_DIR LDCS_RANKINFO` before
invoking the training process) and the detection recipe — not duplicated here to
avoid drift between the two copies.

#### Unified PHYSICAL memory != any host pointer is GPU-addressable (MI300A, ROCm 7.2.1)

Symptom: SIGABRT (rc=134) with repeated `Memory access fault by GPU node-4 ...
Reason: Unknown` on the first kernel, after switching an app to a "plain aligned
host malloc + hipMemAdvise" allocation path on MI300A (RAJAPerf
`--hip-data-space HipHostAdviseFine`, 2026-08-05).

Root cause: MI300A's APU shares HBM *physically* between CPU and GPU, but the GPU
still only addresses ranges that came from a HIP-registered allocation path
(`hipMalloc` / `hipMallocManaged` / `hipHostMalloc`, or an explicit
`hipHostRegister`). `hipMemAdvise` conveys placement/coherence HINTS for an already-
registered range; it does not register or map a plain `malloc`/`aligned_alloc` buffer.

Fix: use `hipMallocManaged` when you want the zero-staging-copy APU behaviour — it
is the same physical HBM with no migration on MI300A, and it removes the pinned-host
staging buffer that discrete-GPU code paths force. Never justify a plain-malloc GPU
access path with "unified memory makes it free".

#### dftracer HIP tracing is a 6-7x observer effect on launch/sync-heavy kernels (2026-08-05)

- **Symptom:** a `HIP_RUNTIME_API` trace bucket implies ~43 us per host-side HIP call, far
  above a bare `hipLaunchKernel` on MI300A (~2-5 us), and the kernels with the most HIP
  calls per unit work look catastrophically slow.
- **Root cause:** every intercepted HIP API call and kernel dispatch pays the tracing cost,
  so the inflation is proportional to CALL COUNT, not to real time - it lands hardest on
  exactly the many-small-launch / many-sync pattern you are trying to diagnose.
- **Measured (RAJAPerf, MI300A/gfx942, ROCm 7.2.1):** kernels issuing 26
  `hipStreamSynchronize` + hundreds of `hipLaunchKernel` per repetition were inflated
  **6.1x-6.7x** in the app's own reported time (0.960 s traced vs 0.144 s untraced p50).
  The traced data supported a conclusion ("the GPU variant is 18x slower than serial") that
  is FALSE untraced.
- **Exact fix:** before sizing any GPU launch-overhead optimization against a
  `HIP_RUNTIME_API` / `KERNEL_DISPATCH` bucket, cross-check against the application's own
  timing output with tracing DISABLED. Keep tracing state identical across optimization
  arms (KB hard rule), but do the BOTTLENECK SIZING untraced.

#### 2026-08-05 (MI300A/gfx942, ROCm 7.2.1): compute-lever no-ops and one live candidate

- `HSA_ENABLE_INTERRUPT=0` (busy-wait GPU completion): **regression on any mixed CPU+GPU app**.
  Measured on RAJAPerf, 5 interleaved replicates, 4N/16R, untraced both arms: GPU-side -1.0%,
  CPU-side +4.0%, net +3.78% WORSE. Busy-polling steals host cores from co-resident CPU work.
  Only consider for a pure-GPU sync-heavy phase with idle host cores.
- `rocm-smi --setperflevel high`: admin-gated on LC systems (no sudo); MI300A already boosts
  under sustained load. Treat as not-tunable rather than untried.
- MIOpen find-mode / vendor conv auto-tune: **not applicable** to apps that emit their own
  HIP kernels (no library conv/GEMM dispatch to tune).
- NUMA/CPU-GPU affinity binding: now a confirmed no-op on this exact MI300A system across
  four distinct workload classes. Do not re-propose without a new mechanism.
- Live candidate for many-small-launch ROCm apps: **HIP graphs** (`hipGraphCreate`/
  `hipGraphInstantiate`/`hipGraphLaunch`) to amortize per-launch driver enqueue cost, the HIP
  analogue of CUDA Graphs kernel batching (Ekelund et al. 2025,
  https://arxiv.org/pdf/2501.09398v1). Size the expected win against an UNTRACED app-timer
  measurement - HIP API tracing inflates exactly this pattern several-fold.
