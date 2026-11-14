---
name: software_ray
description: Ray (Ray Core / Train / Tune / Data) cluster bring-up on Cray PE + ROCm systems: the jemalloc LD_PRELOAD / static-TLS crash that makes `ray start --head` fail (export LD_PRELOAD="" before every ray start), multi-node manual bootstrap pitfalls (RAY_ADDRESS for ray.init, head --num-gpus, worker lifetime), and trace-reading caveats (ray.data materializes once; plasma_store paths in default_worker.py cmdlines). Load for any Ray workload, or on `Failed to connect to GCS at address ... within 5 seconds`, `Failed to get cluster ID from GCS server: TimedOut`, `FileNotFoundError: ... logs/gcs_server.err`, `cannot allocate memory in static TLS block`, a Ray Train job hanging at ~0% CPU waiting for resources, or epoch-boundary POSIX metadata bursts in a ray.data pipeline.
---
Cross-references: [[software_rocm]] [[software_molformer]] [[dftracer_optimize_io]] [[dftracer_diagnose]] [[system_tuolumne]] [[software_flux]] [[capability_builder]]

# software_ray

Converted from dftracer-agents skill `software-ray`. Tools: `software_ray_recipe` (predictor) and `software_ray_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Set `export LD_PRELOAD=""` (empty string, not unset) before EVERY `ray start` (head and each worker's `ray start --address=...`). Ray's start_ray_process() injects LD_PRELOAD=<ray>/core/libjemalloc.so whenever os.environ.get('LD_PRELOAD') is None, which fails under a crowded static-TLS budget (Cray PE + module load rocm).
- Diagnose this class of failure by rebuilding the exact gcs_server/raylet command from ray/_private/services.py (start_gcs_server / start_raylet `command` list), running it by hand with and without the suspected env var, and diffing against the env start_ray_process() uses (os.environ.copy() + env_updates); LD_PRELOAD injection is the first thing to check.
- `ray.init()` with no arguments joins a hand-bootstrapped cluster only if RAY_ADDRESS is set in that process; otherwise it creates an isolated single-node cluster and multi-node ScalingConfig requests hang forever (no error, ~0% CPU).
- If the head is a real accelerator compute node, do not pass --num-gpus=0 / --num-cpus=0 to `ray start --head`; that under-resources the cluster when resource math counts every node.
- Keep worker `ray start --address=...` alive with a completion-marker file written by the head (polled with a generous upper bound), not a fixed `sleep N` before `ray stop`.
- `ray.data.read_csv(...)` materializes once into the object store; workers pull from it, not the file. Resolve FH metadata records to real paths before proposing dataset caching/striping for epoch-boundary metadata bursts.
- Repeated __lxstat64 bursts from new Ray workers are usually Python/venv site-packages import walks (module-import storm), not app I/O.
- Filter `default_worker.py` command-line records before concluding object spilling: every worker cmdline embeds --object-store-name=.../plasma_store (read the trace through dftracer-utils TraceViewer / tools_dftracer_utils, drop records whose text contains default_worker.py, then match '<ray_temp_dir>'; the source skill did this with a decompress | grep -v default_worker.py | grep pipeline).

## Constraints
- Verified on Tuolumne (Cray PE, ROCm 6.2.1, Ray 2.48.0, python3.9); other Ray versions/preloaded libs may differ - re-diagnose with the by-hand command.
- ray start's Python traceback never shows the gcs_server subprocess's own stdout/stderr.

## Corner cases
### `ray start --head` fails after ~35 s: `Failed to connect to GCS ... within 5 seconds`, `Failed to get cluster ID from GCS server: TimedOut`, `FileNotFoundError: .../logs/gcs_server.err`
Cause: jemalloc LD_PRELOAD injected by Ray fails with `cannot allocate memory in static TLS block`; gcs_server never reaches main() so it writes no logs; the Popen handle looks alive so the failure surfaces as a timeout. Fix: export LD_PRELOAD="" before ray start. Verify: head up in ~10 s, `ray status` shows the node.

### Ray Train job hangs indefinitely at near-0% CPU, no error
Cause: ray.init() without RAY_ADDRESS created its own single-node cluster. Fix: export RAY_ADDRESS=<head_ip>:<port> in the driver.

### Worker GPUs vanish mid-job
Cause: worker `sleep N; ray stop` raced the head's job duration. Fix: poll a completion-marker file written by the head.

### Diagnoser flags critical POSIX metadata bursts at epoch boundaries
Cause: worker import storms (117,920 __lxstat64 on site-packages in one run), not dataset re-reads (CSV saw 9 ops / 0.006 s total). Fix: resolve FH paths first.

### Trace grep shows plasma_store/spill paths (2026-08-02)
Cause: --object-store-name in default_worker.py cmdlines. Fix: grep -v default_worker.py before concluding spilling.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_ray_recipe` renders the recipe; validator `software_ray_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `empty_ld_preload_before_ray_start` fails: export LD_PRELOAD="" before every ray start (head and workers). Then render with `software_ray_recipe` and validate again.
- `ray_address_for_init` fails: export RAY_ADDRESS=<head_ip>:<port> before the driver. Then render with `software_ray_recipe` and validate again.
- `head_keeps_gpus` fails: Let the head contribute its devices (omit --num-gpus or set the real count). Then render with `software_ray_recipe` and validate again.
- `no_fixed_sleep_before_ray_stop` fails: Poll a completion-marker file written by the head, with a generous upper bound, then ray stop. Then render with `software_ray_recipe` and validate again.
- `filter_worker_cmdlines_for_spill` fails: Insert grep -v default_worker.py before the plasma_store / <ray_temp_dir> match (on events read through TraceViewer). Then render with `software_ray_recipe` and validate again.

## Self-heal
- If ray start still times out with LD_PRELOAD="", run gcs_server by hand from the services.py command list and diff the environment for another injected variable.

## Self-learn
- Record new Ray-version-specific bring-up failures with the exact command, Ray/ROCm/python versions, and the env diff that fixed them.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_ray via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, Tuolumne Cray PE, ROCm 6.2.1, Ray 2.48.0, python3.9) export LD_PRELOAD="" before ray start --head and every worker ray start --address: head up in ~10 s, ray status active, reproduced across multiple full job launches.
- (2026-08-02, ray_molformer 4-node/16-GPU) filtering default_worker.py cmdline records left 337 ops (logs/sockets/ports_by_node.json/artifact metadata) - zero real spill activity.

## Source: dftracer-agents `software-ray` (verbatim, headings demoted)
_Original description:_ Ray (ray.io) cluster bring-up caveats — the jemalloc/static-TLS `ray start --head` crash on Cray PE + ROCm systems, and multi-node bootstrap pitfalls. Load this skill for any Ray/Ray Train/Ray Tune/Ray Data workload, especially on Cray PE (module-heavy) or ROCm/AMD-GPU systems.

### software-ray

#### `ray start --head` fails with a silent `gcs_server.err: FileNotFoundError` on Cray PE + ROCm systems

**Symptom:** `ray start --head` deterministically fails after ~35 seconds (a 5s GCS-connect
timeout followed by a 30s cluster-ID retry timeout) with:
```
gcs_rpc_client.h:151: Failed to connect to GCS at address <ip>:<port> within 5 seconds.
gcs_client.cc:183: Failed to get cluster ID from GCS server: TimedOut...
FileNotFoundError: [Errno 2] No such file or directory: '<temp_dir>/session_.../logs/gcs_server.err'
```
This reproduces across every combination of `--node-ip-address`, `--num-cpus`/`--num-gpus`,
retry loops, and fresh `--temp-dir`s — the `gcs_server` C++ binary itself, when invoked
DIRECTLY with the exact same flags `ray start` uses (verified by reading
`ray/_private/services.py::start_gcs_server`'s constructed `command` list and reproducing it by
hand), starts and stays running fine, binds its port, and writes its own log files normally.
The difference is invisible from `ray start`'s own Python-side traceback, which only ever shows
the driver's connection-timeout failure, never the `gcs_server` subprocess's own stdout/stderr.

**Root cause:** `ray/_private/services.py::start_ray_process()` unconditionally computes
`jemalloc_env_vars = propagate_jemalloc_env_var(...)`, which sets
`LD_PRELOAD=<ray_install>/core/libjemalloc.so` **whenever `os.environ.get("LD_PRELOAD") is
None`** in the parent process — this applies to EVERY Ray subprocess it spawns (gcs_server,
raylet, workers), not just ones explicitly requesting jemalloc profiling. On a Cray PE system
with `module load rocm/<version>` (or any other environment that already preloads/links a large
number of shared libraries, consuming a big share of glibc's static-TLS surplus), dlopen'ing
jemalloc under that already-crowded static-TLS budget fails with `cannot allocate memory in
static TLS block`. Because this happens during dynamic linking, `gcs_server`'s `exec()` never
reaches `main()` — it writes **zero** log lines, exactly matching the observed
`gcs_server.err: FileNotFoundError` (the file was never created because nothing ever ran to
create it). The parent's `subprocess.Popen` handle can still transiently look "alive" to Ray's
own connection-retry loop (`node.py::_init_gcs_client`), which is why the failure surfaces 30+
seconds later as a confusing timeout rather than an immediate, obvious crash.

**Fix:** explicitly set `LD_PRELOAD` to an EMPTY STRING (not merely unset — `os.environ.get(...)
is None` must be `False`) before any `ray start` invocation:
```bash
export LD_PRELOAD=""
ray start --head ...
```
Do this before every `ray start` call in a multi-node bring-up script (head AND each worker's
`ray start --address=...`, since raylet is spawned by the worker call too and is equally
susceptible). Verified: `ray start --head` then succeeds in ~10s and `ray status` reports the
node active, reproduced across multiple full job launches on Tuolumne (Cray PE, ROCm 6.2.1,
Ray 2.48.0, python3.9).

**How to diagnose this class of bug if it recurs (different Ray version / different preloaded
lib):** reproduce the exact `gcs_server`/`raylet` command line by reading
`ray/_private/services.py::start_gcs_server`/`start_raylet` (the constructed `command` list),
then run that binary directly by hand with and without your suspected env var — if it starts
fine standalone but fails only under `ray start`, diff the env `start_ray_process()` actually
uses (`modified_env = os.environ.copy(); modified_env.update(env_updates)`) against your manual
invocation; `LD_PRELOAD` injection is the first thing to check.

#### Multi-node manual bring-up: other pitfalls (not jemalloc-specific)

- `ray.init()` with no arguments does NOT auto-join a cluster you bootstrapped by hand with
  `ray start --head` unless `RAY_ADDRESS` is set in that process's environment — otherwise it
  silently creates its own new, isolated single-node cluster, and any `ScalingConfig`/resource
  request sized for the intended multi-node cluster will hang forever waiting for resources
  that will never appear (no error, no traceback — just near-0% CPU indefinitely).
- If a head node is a real accelerator-bearing compute node (not a control-plane-only login
  node), don't reflexively pass `--num-gpus=0`/`--num-cpus=0` to `ray start --head` — that
  under-resources the cluster if your `ScalingConfig`/resource math assumes every physical
  node (including the head) contributes its full device count.
- A worker script that keeps its `ray start --address=...` process (and thus its GPUs) alive
  via a fixed `sleep N` before `ray stop` is a race against the actual head-side job duration.
  Prefer a completion-marker file the head writes on exit, polled by the worker with a generous
  upper bound, over guessing a sleep duration.

#### `ray.data.read_csv(...)` materializes once into the object store — do not assume per-epoch re-reads

A diagnoser flagging "critical" POSIX metadata-op-count bursts at epoch boundaries in a
`ray.data` training pipeline does NOT mean the dataset file is being re-opened/re-read each
epoch — verify by resolving the trace's `FH` metadata records to real paths before proposing
any dataset-caching/striping fix. Measured on a 2-node Ray Train run (MoLFormer, 4 epochs):
the source CSV saw 9 POSIX ops / 0.006s for the ENTIRE run (all in the driver process, at
initial `read_csv()` time), and **zero** further opens/reads from any worker across all 4
epochs of `dataset.iter_batches()` — Ray keeps the materialized data resident in the object
store and workers pull from there, not the file. If you see repeated metadata bursts anyway,
resolve the actual `FH` paths first: on that same run, 117,920 of the observed `__lxstat64`
calls were the Python interpreter/venv `site-packages` import path being walked repeatedly by
newly-spawned Ray worker processes (a dynamic-loading/module-import storm, not app I/O) — see
`dftracer-io-optimization` for the general version of this lesson.

#### `plasma_store` path strings in a trace can be `default_worker.py` command-line args, not real spill files

Confirmed on ray_molformer (2026-08-02, 4-node/16-GPU): a raw grep for `plasma_store`/spill
paths in a trace can false-positive, because Ray embeds
`--object-store-name=.../plasma_store` in every `default_worker.py` process's command-line
string, which shows up in trace/process metadata and looks like a file access even when it
isn't one. Filter out cmdline records before concluding real object spilling occurred, e.g.
`zcat *.pfw.gz | grep -v default_worker.py | grep '<ray_temp_dir>'`. On ray_molformer the
filtered result was 337 ops, all logs/sockets/`ports_by_node.json`/artifacts metadata — zero
real spill activity, confirming the diagnosis was I/O-negligible rather than spill-bound.
