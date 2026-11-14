---
name: system_tioga
description: System profile for tioga (LLNL Cray EX, AMD MI250X gfx90a, 8 GCDs/node, EPYC 7A53 Trento 64 cores, Flux): same software stack as Tuolumne (rocm/6.4.2, rocmcc/6.4.2-cce-20.0.0-magic, cray-mpich/9.0.1, papi/7.2.0.2; binaries portable) but different hardware, queues, PAPI presets and Lustre. Load for any dftracer session, build or job launch on tioga, or when a job sits in S forever (pall scheduling stopped, drained nodes, cores exhausted by dftracer_service), on 'flux-alloc: ERROR: queue "pllm" not valid for user', a gfx942 binary whose kernels do not run, missing PAPI_L2_TCM / PAPI_L2_TCH / PAPI_FMA_INS, a multi-rank traced GPU run SIGSEGV at >= 3 ranks, zero variorum power events, 'corrupted size vs. prev_size in fastbins' at service teardown, or a dangling /p/lustre5 dataset symlink.
---
Cross-references: [[system_tuolumne]] [[software_papi]] [[software_rocm]] [[software_flux]] [[workload_genesis_run]] [[tools_dftracer]] [[tools_dftracer_utils]] [[software_cupti]] [[capability_builder]]

# system_tioga

Converted from dftracer-agents skill `system-tioga`. Tools: `system_tioga_recipe` (predictor) and `system_tioga_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Tuolumne recipes port, Tuolumne numbers do not: re-derive GPU counts, ppn ladders, PAPI sets and Lustre paths here.
- GPU ppn ladder is 1,2,4,8 (8 MI250X GCDs per node); OpenMP/HIP offload must target gfx90a, never gfx942.
- MI250X is discrete: MEMORY_COPY / PAGE_MIGRATION event volumes are not comparable with Tuolumne's APU.
- Before sizing an allocation check, in order: `flux queue list` (limits, ST), `flux queue status` (pall: 'Scheduling is stopped'), `flux resource list` (free vs down per queue), then a throwaway `flux alloc` (account queue authorization).
- Never use queue pall (submission enabled, scheduling stopped: jobs sit S forever). pdebug (default) is the workhorse: 8 nodes, 12 h. pllm (18 nodes, 1 d) is often not authorized. pci: 4 nodes, 2 h.
- Size the allocation to free nodes, not the advertised maximum; if the largest cells cannot fit in what is free, say so and stop rather than chaining allocations that can never start.
- Because pdebug allows 12 h, a whole sweep usually fits in one allocation - no Tuolumne-style allocation chaining.
- Reserve one core per node for dftracer_service: cores per rank = floor((64 - 1) / max_ppn) (ppn=8 -> 7, not 8).
- Modules (same as Tuolumne): rocm/6.4.2, rocmcc/6.4.2-cce-20.0.0-magic, cray-mpich/9.0.1, papi/7.2.0.2 (known-safe pin); probe papi/7.3.0.1 before trusting it. Default env PrgEnv-cray/8.7.0 + cce/20.0.0; ROCm up to 7.2.1 available.
- PAPI: derive the counter partition from tioga's papi_avail (27 presets, 5 derived, 5 counters) and probe-verify args.multiplex == 0; never copy Tuolumne's partition.
- Application data on /p/lustre1/$USER (main) - /p/lustre2 also writable; dftracer traces stay in the session workspace under genesis_traces/, never on Lustre. /p/lustre5 is not mounted.
- `dftracer_service start` must be launched with `flux submit` (detached) and polled via per-host pid files, never `flux run`.
- Pin service start, app and service stop to the same hosts with `--requires=host:`.
- Build dftracer with DFTRACER_BUILD_VARIORUM=ALWAYS (AUTO finds the system RPM that yields zero power events) and verify a gpu/power event lands.
- If a multi-rank traced GPU run dies at init with no output, confirm the dftracer build has the BufferManager `ready` guard first.

## Constraints
- NFS workspace is shared with Tuolumne (session workspaces cross machines); Lustre is NOT shared (tioga /p/lustre1, /p/lustre2; Tuolumne /p/lustre5).
- GPU hardware counters are unavailable (ROCProfiler lacks SYS_PERFMON); GPU activity tracing works.
- Audits that parse application results must run where that PFS is mounted.
- A Tuolumne-built dftracer runs unmodified here; tioga is a legitimate place to post-process a Tuolumne corpus.

## Corner cases
### Job submitted to pall stays `S` forever
`flux queue status`: 'pall: Scheduling is stopped'. flux queue list looks healthy. Use pdebug.

### `flux-alloc: ERROR: queue "pllm" not valid for user; valid queues for user: pdebug,pci`
pllm shows enabled with free nodes in flux queue list but the account is not authorized; only a submit reveals it. Use pdebug/pci.

### Sweep sits in SCHED forever, looks like a busy cluster
Large fraction of nodes drained: observed pdebug 2 of 8 free, pci 0 of 4, for > 16 h. Check `flux resource list`; size to free nodes; stop if the largest cells cannot fit.

### Application job never schedules at max ppn (sits S, no error)
dftracer_service holds one core per node; 64/ppn per rank requests every core. Measured ppn=8: 8 cores/rank deadlocks, 7 works. Use floor((64-1)/max_ppn).

### Kernels do not run from a Tuolumne-built offload binary
Built for gfx942 (MI300A); tioga is gfx90a. Rebuild targeting gfx90a.

### PAPI counter set from Tuolumne fails / multiplexes
tioga lacks PAPI_L2_TCM, PAPI_L2_TCH, PAPI_FMA_INS; PAPI_L2_ICM, PAPI_FP_INS, PAPI_FML_INS, PAPI_FAD_INS, PAPI_FDV_INS, PAPI_FSQ_INS are native here (derived on Tuolumne) so sets pack differently. Re-derive from papi_avail.

### papi/7.3.0.1 SIGSEGV at PAPI_library_init (Tuolumne)
rocp_sdk component ABI-incompatible with ROCm 6.4.2 on Tuolumne. tioga has newer ROCm so it may work - probe first; 7.2.0.2 is the known-safe pin.

### Traced multi-rank GPU run SIGSEGV at >= 3 total ranks (clean at 1-2, invisible under gdb)
BufferManager two-phase construction: rocprofiler (registered via rocprofiler_configure before dftracer init) flushes into a null config in log_data_event(). Fixed by a `ready` atomic set at the end of initialize() and cleared at finalize() guarding all log_*_event entry points (HIP, CUDA, PAPI sampler, brahma). Confirm the build carries it.

### `dftracer_service start` under `flux run` never returns
Use `flux submit` detached and poll per-host pid files.

### Service start / app / stop land on different nodes
In an allocation larger than the job each gets a different node subset. Pin all three with --requires=host:.

### Zero power events with DFTRACER_BUILD_VARIORUM=AUTO; `_ERROR_VARIORUM_UNSUPPORTED_PLATFORM`
AUTO picks the system variorum RPM. Use DFTRACER_BUILD_VARIORUM=ALWAYS and verify a gpu/power event lands.

### `corrupted size vs. prev_size in fastbins` abort at dftracer_service teardown
Two librocm_smi64 ABIs mapped (.so.1 via libhwloc, .so.7 via libvariorum). Strictly post-flush, no data lost. HWLOC_COMPONENTS=-rsmi does not avoid it (.so.1 is a link-time DT_NEEDED).

### ROCProfiler: 'could not be locked for profiling due to lack of permissions (capability SYS_PERFMON)'
GPU activity tracing (kernel dispatch, memory copy, page migration) unaffected; GPU hardware counters unavailable.

### Traces readable but app output (checkpoints, results) missing
dataset/ symlink onto Tuolumne's /p/lustre5 dangles on tioga. `ls -d /p/lustre*` before assuming a session is usable; run result audits where the PFS is mounted.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `system_tioga_recipe` renders the recipe; validator `system_tioga_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_pall_queue` fails: Use -q pdebug (8 nodes, 12 h). Then render with `system_tioga_recipe` and validate again.
- `no_gfx942` fails: Target gfx90a. Then render with `system_tioga_recipe` and validate again.
- `pdebug_max8` fails: Size to free nodes from flux resource list (<= 8). Then render with `system_tioga_recipe` and validate again.
- `no_variorum_auto` fails: Use DFTRACER_BUILD_VARIORUM=ALWAYS and verify a power event lands. Then render with `system_tioga_recipe` and validate again.
- `service_start_via_submit` fails: flux submit it detached and poll per-host pid files. Then render with `system_tioga_recipe` and validate again.
- `service_hosts_pinned` fails: Pin all three with --requires=host:<hosts>. Then render with `system_tioga_recipe` and validate again.
- `no_lustre5` fails: Use /p/lustre1/$USER. Then render with `system_tioga_recipe` and validate again.
- `no_tuolumne_only_presets` fails: Re-derive the counter set from tioga's papi_avail. Then render with `system_tioga_recipe` and validate again.
- `queue_status_checked` fails: Run flux queue status (and flux resource list) before allocating. Then render with `system_tioga_recipe` and validate again.
- `resource_list_checked` fails: Run flux resource list and size to free nodes. Then render with `system_tioga_recipe` and validate again.
- gfx942 -> gfx90a on tioga.
- Queue pall -> pdebug.

## Self-heal
- If a job sits S/SCHED with no error: check flux queue status (pall stopped), flux resource list (drained), and per-rank cores vs 63 usable cores before assuming a busy cluster.
- If a traced multi-rank run dies at init, check the BufferManager ready guard in the dftracer build before anything else.

## Self-learn
- Record whether papi/7.3.0.1 initializes cleanly on tioga once probed, with the ROCm version and date.
- Record queue drain state and queue authorization observations with a date; they change.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this system goes into system_tioga via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated) A dftracer built on Tuolumne (e.g. dftracer_split) runs unmodified on tioga.
- (undated) ppn=8 with 7 cores per rank schedules alongside dftracer_service (8 deadlocks).
- (undated) Every Tuolumne-pinned module is present: rocm/6.4.2, rocmcc/6.4.2-cce-20.0.0-magic, cray-mpich/9.0.1, papi/7.2.0.2, papi/7.3.0.1.

## Source: dftracer-agents `system-tioga` (verbatim, headings demoted)
_Original description:_ System profile for Tioga (LLNL AMD MI250X / Cray PE, Flux) — how it differs from Tuolumne despite sharing the LC software stack, the queue that silently never schedules, the 8-GCD-per-node GPU ladder, the per-system PAPI preset set, and which Tuolumne lessons carry over unchanged. Load this for any dftracer session, build, or job launch on tioga.

### system-tioga

Tioga is an LLNL Cray EX system. It shares Tuolumne's **software** stack almost exactly
but **not** its hardware, so Tuolumne recipes port cleanly while Tuolumne *numbers* do
not. Getting that distinction wrong is the main way to waste a run here.

#### Hardware — NOT the same as Tuolumne

| | Tioga | Tuolumne |
| --- | --- | --- |
| GPU | **MI250X**, `gfx90a` | MI300A (APU), `gfx942` |
| GPUs per node | **8 GCDs** | 4 |
| CPU | **AMD EPYC 7A53 (Trento)**, 64 cores / 128 threads | 96 cores |
| NUMA domains | 4 | |
| `craype` arch | `craype-x86-trento` | |

Consequences:

* The **GPU process-per-node ladder is 1,2,4,8** (8 GCDs), not Tuolumne's 1,2,4.
* Any OpenMP target-offload build must target **`gfx90a`**, not `gfx942`. A binary
  built for `gfx942` on Tuolumne will not run its kernels here.
* MI250X is a discrete GPU, not an APU, so host/device transfers are real PCIe/Infinity
  Fabric copies. `MEMORY_COPY` and `PAGE_MIGRATION` event volumes are not comparable
  with Tuolumne's.

#### Queues — `pall` accepts jobs and never runs them

```
flux queue status
  pall: Job submission is enabled
  pall: Scheduling is stopped        <-- submits fine, sits forever
```

| Queue | Nodes | Time limit | Notes |
| --- | --- | --- | --- |
| `pdebug` (default) | 8 | **12 h** | the workhorse here — far more generous than Tuolumne's 1 h pdebug |
| `pllm` | 18 | 1 d | largest node count, but **often not authorized** — see below |
| `pci` | 4 | 2 h | |
| `pall` | 30 | 1 d | **scheduling stopped — do not use** |

**Always check `flux queue status`, not just `flux queue list`.** `flux queue list` shows
`pall` with healthy-looking limits; only `flux queue status` reveals that its scheduler is
stopped. A job submitted there stays `S` forever and looks like a busy cluster.

Because `pdebug` allows 12 h, the allocation-chaining that Tuolumne's 1 h limit forces is
usually unnecessary here — a whole sweep normally fits in one allocation.

##### Advertised nodes are not available nodes — check drain state before planning a sweep

Tioga is a small machine and a large fraction of it is routinely **drained**. Observed
state during one sweep, for over 16 hours with no change:

```
free  pllm,pall     11    tioga[13-19,21-23,25]
free  pdebug,pall    2    tioga[34,39]          <-- pdebug advertises 8
down  pdebug,pall    6    tioga[35-38,40-41]
down  pci,pall       4    tioga[30-33]          <-- ALL of pci
down  pllm,pall      7    tioga[12,20,24,26-29]
```

So the queue table's node counts were fiction: `pdebug` could supply **2 of 8**, and
`pci` **0 of 4**. Any sweep cell needing ≥4 nodes was unrunnable, indefinitely.

**`pllm` may not be authorized for your account**, even though `flux queue list` shows
it enabled and with free nodes. The rejection only appears at submit time:

```
flux-alloc: ERROR: queue "pllm" not valid for user; valid queues for user: pdebug,pci
```

Check the three things before sizing an allocation, in this order — each catches a
failure the previous one misses:

1. `flux queue list` — limits and whether scheduling is enabled (`ST` column)
2. `flux resource list` — how many nodes are actually `free` vs `down` per queue
3. a throwaway `flux alloc` — the only way to learn your account's queue authorization

A sweep planned off (1) alone will sit in `SCHED` forever and read exactly like a busy
cluster. **Size the allocation to free nodes, not to the queue's advertised maximum**,
and when the largest remaining cells cannot fit in what is free, say so and stop rather
than chaining allocations that can never start — a driver retrying an impossible request
burns its allocation budget on `rc=1` and accomplishes nothing.

#### Software stack — same as Tuolumne, and binaries are portable

Every module Tuolumne pins is present on tioga (verified): `rocm/6.4.2`,
`rocmcc/6.4.2-cce-20.0.0-magic`, `cray-mpich/9.0.1`, `papi/7.2.0.2`, `papi/7.3.0.1`.
ROCm is available up to `7.2.1`; default env is `PrgEnv-cray/8.7.0` + `cce/20.0.0`.

A dftracer built on Tuolumne **runs unmodified on tioga** (verified: the Tuolumne-built
`dftracer_split` executes here). The `/usr/WS2` and `/usr/workspace` filesystems are
shared, so a session workspace created on one machine is directly usable on the other.
This makes tioga a legitimate place to post-process a Tuolumne corpus.

#### Parallel filesystems are NOT shared with Tuolumne

`/usr/WS2` and `/usr/workspace` (NFS) **are** shared, so a session workspace crosses
machines fine. The **Lustre** mounts do not: tioga has `/p/lustre1` and `/p/lustre2`,
while Tuolumne uses `/p/lustre5`.

**`/p/lustre1` is tioga's main Lustre — use `/p/lustre1/$USER` for application data.**
`/p/lustre2` is also mounted and writable but is not the default choice. Both are ~24 PB.
Per [[feedback-lustre-io]]: application data (datasets, checkpoints, per-run output) goes
to Lustre; dftracer **traces** stay in the session workspace under `genesis_traces/`,
never on Lustre.

This bites whenever a session's `dataset/` is a symlink onto the other machine's Lustre:
the traces (in the workspace, on NFS) are readable here, but the **application's own
output** (checkpoints, result files) silently is not — the symlink dangles. Any audit
that parses app results must run where that PFS is mounted. Check with
`ls -d /p/lustre*` before assuming a session is fully usable from here.

#### PAPI — re-derive the counter set, never copy Tuolumne's

Same budget, **different preset set**:

| | Tioga | Tuolumne |
| --- | --- | --- |
| Hardware counters | 5 | 5 |
| Presets available | **27** | 30 |
| Derived presets | **5** | 12 |

Tioga's derived presets (each costs >= 2 of the 5 counters):
`PAPI_TLB_IM`, `PAPI_BR_UCN`, `PAPI_BR_TKN`, `PAPI_BR_NTK`, `PAPI_BR_PRC`

The 27 available presets:

```
PAPI_BR_CN    PAPI_BR_INS   PAPI_BR_MSP   PAPI_BR_NTK*  PAPI_BR_PRC*
PAPI_BR_TKN*  PAPI_BR_UCN*  PAPI_FAD_INS  PAPI_FDV_INS  PAPI_FML_INS
PAPI_FP_INS   PAPI_FP_OPS   PAPI_FSQ_INS  PAPI_L1_DCA   PAPI_L1_DCM
PAPI_L2_DCH   PAPI_L2_DCM   PAPI_L2_DCR   PAPI_L2_ICA   PAPI_L2_ICH
PAPI_L2_ICM   PAPI_L2_ICR   PAPI_TLB_DM   PAPI_TLB_IM*  PAPI_TOT_CYC
PAPI_TOT_INS  PAPI_VEC_INS                       (* = derived)
```

Tioga does **not** have `PAPI_L2_TCM`, `PAPI_L2_TCH`, or `PAPI_FMA_INS`, all of which
exist on Tuolumne. Conversely several presets that are *derived* on Tuolumne
(`PAPI_L2_ICM`, `PAPI_FP_INS`, `PAPI_FML_INS`, `PAPI_FAD_INS`, `PAPI_FDV_INS`,
`PAPI_FSQ_INS`) are **native** here, so they cost one counter instead of two and pack
differently.

A Tuolumne counter partition therefore fails on tioga twice over: it requests presets
that do not exist, and it mis-sizes the sets. Derive the partition from this machine's
`papi_avail` and probe-verify `args.multiplex == 0`. See [[software-papi]].

The `papi/7.3.0.1` vs `7.2.0.2` question is open here: on Tuolumne 7.3.0.1 SIGSEGVs at
`PAPI_library_init` because its `rocp_sdk` component is ABI-incompatible with ROCm 6.4.2
(see [[bug-cray-papi-731-rocp-sdk-abi-segfault]]). Tioga has newer ROCm available, so
7.3.0.1 *may* be fine — but **probe it before trusting it**; `7.2.0.2` is the known-safe
pin and is present.

#### dftracer BufferManager init race — FIXED, but check your build has it

Any traced multi-rank GPU run here SIGSEGV'd at **>= 3 total ranks** (clean at 1-2,
reproducible 3/3, invisible under gdb) until a dftracer fix landed. Root cause was not
tioga-specific but tioga exposes it: `BufferManager` uses two-phase construction, so
`Singleton<BufferManager>::get_instance()` publishes a pointer whose `config` is still
null until `initialize()` runs. rocprofiler — registered at load time via the exported
`rocprofiler_configure`, before dftracer initialises — flushes from its own thread pool
into that window and dereferences null in `log_data_event()`.

The fix adds a `ready` atomic to `BufferManager`, set at the end of `initialize()` and
cleared at the start of `finalize()`, guarding all three `log_*_event` entry points. It
covers every asynchronous producer (HIP, CUDA, PAPI sampler, brahma), not just HIP.

If a multi-rank run here dies at init with no output, confirm your dftracer build carries
that guard before looking anywhere else.

#### Reserve a core for dftracer_service when sizing per-rank cores

A tioga node has **64 cores** and `dftracer_service` holds **one per node** for the whole
run. Sizing per-rank cores as `64 / max_ppn` therefore makes the largest ppn request every
core on the node, and the application job can never be scheduled -- it sits in `S`
**forever** rather than failing. Measured: at ppn=8, 8 cores/rank deadlocks and 7 works.
Use `floor((cores_per_node - 1) / max_ppn)`.

#### What carries over from Tuolumne unchanged

These are software-stack behaviours, not hardware, so they apply here as-is:

* `dftracer_service start` under `flux run` never returns — use `flux submit` detached
  and poll the per-host pid files. See [[bug-dftracer-service-start-blocks-flux-run]].
* Service start / app / service stop must all be pinned to the **same** hosts with
  `--requires=host:`, or in an allocation larger than the job they each get a different
  node subset. See [[bug-dftracer-service-hosts-must-be-pinned]].
* `DFTRACER_BUILD_VARIORUM=AUTO` finds a system variorum RPM that reports
  `_ERROR_VARIORUM_UNSUPPORTED_PLATFORM` and yields **zero** power events; use
  `DFTRACER_BUILD_VARIORUM=ALWAYS`. Verify a `gpu`/`power` event actually lands.
* The `dftracer_service` process maps two `librocm_smi64` ABIs (`.so.1` via libhwloc,
  `.so.7` via libvariorum) and aborts at teardown with `corrupted size vs. prev_size in
  fastbins`. It is strictly **post-flush** and costs no data. `HWLOC_COMPONENTS=-rsmi`
  does not avoid it (`.so.1` arrives via a link-time `DT_NEEDED`).
* ROCProfiler logs `could not be locked for profiling due to lack of permissions
  (capability SYS_PERFMON)`. GPU **activity** tracing (kernel dispatch, memory copy,
  page migration) is unaffected; GPU **hardware counters** are unavailable.

#### Related

[[system-tuolumne]] for the sibling MI300A system, [[software-papi]] for the counter
partition method, [[software-rocm]] for HIP/rocprofiler generics, [[flux-alloc]] for
allocation mechanics, [[genesis_run]] for the sweep harness that consumes all of this.
