---
name: software_mpi
description: MPI and MPI-IO (ROMIO) knowledge for dftracer work: ROMIO hints files vs Cray MPICH MPICH_MPIIO_HINTS (pattern:key=value:key=value format), the confirmed hint set on cray-mpich 9.0.1, storage-specific guidance (cb_read hurts and ds_write=disable is fatal on VAST NVMe), cb_nodes being accepted but ignored on Cray MPICH without CRAY_CB_NODES_MULTIPLIER, env propagation through mpirun -x / flux run --env / wrapper scripts, building dftracer with DFTRACER_ENABLE_MPI, the mpi.h include-path issue in clang_syntax_check, mpi4py on Cray MPICH (libmpi.so.12 vs libmpi_cray.so.12), and reading MPI_Barrier as a load-imbalance sink. Load for any MPI or collective I/O work, or on: MPICH_MPIIO_HINTS lost/binary missing under flux run --env, 'unrecognized value' for a hint, hints echoed but aggregator count stuck at 2, 'fatal error: mpi.h: No such file or directory', 'RuntimeError: cannot load MPI library ... libmpi.so.12', no MPI_File_* events in the trace, MPI_Barrier dominating a profile.
---
Cross-references: [[software_hdf5]] [[software_flux]] [[software_rocm]] [[software_pip]] [[system_tuolumne]] [[tools_dftracer]] [[tools_dftracer_utils]] [[dftracer_optimize_io]] [[dftracer_trace]] [[dftracer_pipeline]] [[dftracer_annotate_clang]] [[workload_ior]] [[workload_h5bench]] [[workload_flashx]] [[workload_scaffold]] [[workload_rajaperf]] [[capability_builder]]

# software_mpi

Converted from dftracer-agents skill `software-mpi`. Tools: `software_mpi_recipe` (predictor) and `software_mpi_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- MPI-IO/ROMIO L2 tuning applies when the bottleneck is small_io_pct or rand_pct high (metric: bandwidth or time).
- On Cray MPICH prefer `MPICH_MPIIO_HINTS` over a ROMIO_HINTS file. Format: `pathname_pattern:key=value:key=value`, colon-separated pairs per pattern, comma-separated patterns, `*` matches all files. `MPICH_MPIIO_HINTS_DISPLAY=1` prints the applied hints.
- NEVER pass MPICH_MPIIO_HINTS via `--env` to `flux proxy ... flux run`: the colons/semicolons make flux run lose the binary argument. Export it in a wrapper script (`export ...; exec "$@"`) and run `flux run ... bash wrapper.sh <binary> <args>`. (The source skill's generic flux --env example that includes MPICH_MPIIO_HINTS is superseded by this rule.)
- Discover the hints a Cray MPICH build supports with `strings <cray-mpich>/lib/libmpi_cray.so | grep -E "^romio_|^cb_|^striping_|^ind_|^ds_" | sort -u`.
- `romio_no_indep_rw` is NOT supported on cray-mpich 9.0.1: silently dropped with an 'unrecognized value' warning.
- Check FS_TYPE before applying ROMIO hints: collective read buffering helps high-latency storage (Lustre, disk) and hurts parallel NVMe. On VAST: romio_cb_write=enable +58% write BW, romio_cb_read=enable -70% read BW (avoid), romio_ds_write=disable FATAL (352 -> 95 MiB/s).
- cb_nodes on Lustre + cray-mpich 9.0.1 (Tuolumne lustre5, 2 nodes x 192 ranks): do NOT set for contiguous fixed-size or variable-size writes (default 2 aggregators); reads untested (2x stripe_count per literature). If needed, test at each scale step first.
- On Cray MPICH `cb_nodes` alone is accepted (echoed by MPICH_MPIIO_HINTS_DISPLAY) but IGNORED: the aggregator count stays 2. Raise it with `CRAY_CB_NODES_MULTIPLIER` together with cb_nodes and a wide enough Lustre stripe count.
- Verify the real aggregator count from the trace: count distinct pids issuing pwrite/write with ret >= 1 MiB, never from the hints display and never 'ranks that write' (logs write on every rank).
- Collective-buffering hints are worthless until the application performs parallel writes: if one rank holds ~all write bytes, fix that first (workload_flashx serial-HDF5 case).
- mpirun does not forward the shell environment: export and pass each var with `-x` (DFTRACER_ENABLE, DFTRACER_INIT, DFTRACER_DATA_DIR, DFTRACER_LOG_FILE, MPICH_MPIIO_HINTS, LD_LIBRARY_PATH, LD_PRELOAD).
- `flux proxy` does not export the current shell's environment to job tasks: pass variables with `flux run --env VAR=value` (or a wrapper script for values with colons); `export` before flux proxy does not propagate.
- dftracer must be built with `-DDFTRACER_ENABLE_MPI=ON` to capture MPI_File_* events; verify `#define DFTRACER_MPI_ENABLE 1` in `<prefix>/include/dftracer/core/dftracer_config.hpp`. The run-time MPI library must match the one dftracer was compiled against (`strings libdftracer_core.so | grep include` vs the system mpi.h path).
- Cray PE `mpicc --showme:incdirs` returns `-I/path`, breaking auto-detection in clang_syntax_check: pass extra_include_dirs explicitly (the cray-mpich include dir from `mpicc -show | grep -o '\-I[^ ]*' | head -1`, and the venv's dftracer/include).
- NUMA binding: `numactl --hardware`, `numactl --cpunodebind=0 --membind=0 <cmd>`; OpenMPI `mpirun --map-by numa:pe=<cores_per_node>`.
- A dominating MPI_Barrier is usually a load-imbalance sink: attack the upstream imbalance (e.g. dataloader_num_workers > 0), no barrier surgery; rank by wall clock / FOM, and confirm the barrier aggregate is a meaningful fraction of wall clock from a run long enough (>= ~10 min training, fixed budget) before acting.
- Before proposing a communication fix for barrier time, `grep -rn MPI_Barrier` the source and classify call sites harness vs algorithmic; harness barriers (IOR timing loop, RAJAPerf startTimer/stopTimer) are off-limits, leaving collective-algorithm selection (MPICH_SHARED_MEM_COLL_OPT=1, prior on Tuolumne: no_change -1.6%).
- Check the Failed Configurations log before proposing a configuration for a workload/software/filesystem; the optimization loop appends entries (date, app, workload, filesystem, system, bottleneck, config_attempted, result, metrics_before, metrics_after, delta, root_cause, do_not_use_when).

## Constraints
- Hint guidance is per (system, filesystem, MPI version): the cray-mpich 9.0.1 table and cb_nodes rules were measured on Tuolumne lustre5 (28 OSTs) and VAST.
- 'Do-less' levers (e.g. raising checkpoint_interval) are not speedups: verify total bytes unchanged before crediting.
- comparator barrier p50 can be pinned to a fixed time bucket (167.79 ms): use mean/p95/p99 and wall clock instead.
- `--no-binary=mpi4py` does not work on Python 3.13 + NFS (pip atomic rename fails).

## Corner cases
### flux run loses the binary argument when `--env MPICH_MPIIO_HINTS=...` is passed
Cause: colons/semicolons in the value. Fix: export MPICH_MPIIO_HINTS in a wrapper.sh that ends in `exec "$@"` and run `flux proxy $JOB flux run ... bash wrapper.sh <binary> <args>`.

### `romio_no_indep_rw` hint dropped with 'unrecognized value'
Not supported on cray-mpich 9.0.1. Remove it.

### `MPICH_MPIIO_HINTS_DISPLAY=1` shows `cb_nodes = 8` but only 2 aggregators write
Cray MPICH ignores cb_nodes alone. Fix: cb_nodes + CRAY_CB_NODES_MULTIPLIER + wide Lustre stripe. Verify by counting distinct pids with >= 1 MiB pwrite/write in the trace. Measured Flash-X 384 ranks: 2 -> 16 aggregators, critical-path write 6.80 s -> 1.45 s (2026-07-08).

### Write bandwidth collapses 352 -> 95 MiB/s on VAST
Cause: romio_ds_write=disable. FATAL on VAST; keep data-sieving writes enabled there.

### Read bandwidth -70% on VAST after romio_cb_read=enable
Collective read buffering hurts parallel NVMe; disable it on VAST, keep it for Lustre.

### segfault with cb_nodes=16 + cb_buffer_size + striping hints
Seen in h5bench (see workload_h5bench). cb_nodes=32 alone (16-OST) neutral; cb_nodes=56 alone (28-OST) close -96% but pwrite p95 +2650%.

### `fatal error: mpi.h: No such file or directory` in clang_syntax_check
Cray PE mpicc prints include dirs with a -I prefix, so auto-detection fails. Pass extra_include_dirs=[<cray-mpich include>, <venv>/site-packages/dftracer/include].

### `RuntimeError: cannot load MPI library ... libmpi.so.12: cannot open shared object file`
mpi4py manylinux wheel expects libmpi.so.12; Cray PE ships libmpi_cray.so.12. Fix: download + unzip the wheel, patchelf RPATH to <venv>/lib:<cray-mpich lib>, symlink libmpi_cray.so.12 as <venv>/lib/libmpi.so.12, re-zip, install with MPI4PY_MPIABI=mpich; persist MPI4PY_MPIABI and LD_LIBRARY_PATH in the session env script.

### No MPI_File_* events in the trace
dftracer built without DFTRACER_ENABLE_MPI=ON or the run-time MPI differs from the compile-time one. Check dftracer_config.hpp for DFTRACER_MPI_ENABLE 1.

### MPI_Barrier is ~99% of MPI time
Usually a sink for upstream imbalance, or a short-run artifact (2 s run; at 12 min on ScaFFold it was 16.8 s of 749.9 s, ~2%). Or a benchmark timing-harness barrier (IOR, RAJAPerf). Mean barrier rising while wall falls is a sink tell.

### Env vars exported before `flux proxy` not seen by job tasks
flux proxy does not export the shell environment. Use flux run --env (or a wrapper script).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_mpi_recipe` renders the recipe; validator `software_mpi_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_mpiio_hints_via_flux_env` fails: Export MPICH_MPIIO_HINTS in a wrapper script ending in exec "$@" and run flux run ... bash wrapper.sh <binary>. Then render with `software_mpi_recipe` and validate again.
- `mpiio_hints_have_pattern` fails: Prefix with '*:' (all files) or a file pattern. Then render with `software_mpi_recipe` and validate again.
- `mpiio_hints_colon_separated` fails: Use *:k1=v1:k2=v2. Then render with `software_mpi_recipe` and validate again.
- `no_romio_no_indep_rw` fails: Remove romio_no_indep_rw. Then render with `software_mpi_recipe` and validate again.
- `no_ds_write_disable_on_vast` fails: Keep romio_ds_write enabled (default) on VAST. Then render with `software_mpi_recipe` and validate again.
- `no_cb_read_on_vast` fails: Use romio_cb_read=disable (or leave unset) on VAST. Then render with `software_mpi_recipe` and validate again.
- `cray_cb_nodes_needs_multiplier` fails: Add export CRAY_CB_NODES_MULTIPLIER=<k> (and a wide Lustre stripe); verify aggregators from the trace. Then render with `software_mpi_recipe` and validate again.
- `mpirun_forwards_dftracer_env` fails: Pass -x DFTRACER_ENABLE -x DFTRACER_INIT -x DFTRACER_DATA_DIR -x DFTRACER_LOG_FILE -x LD_LIBRARY_PATH -x LD_PRELOAD. Then render with `software_mpi_recipe` and validate again.
- `mpi4py_cray_abi` fails: Patch the wheel (patchelf RPATH + libmpi.so.12 symlink) and install with MPI4PY_MPIABI=mpich. Then render with `software_mpi_recipe` and validate again.
- `no_mpi4py_no_binary` fails: Download and extract the wheel manually, patch, re-zip, install. Then render with `software_mpi_recipe` and validate again.
- Any hint change: re-measure the real aggregator count and wall clock; record regressions in the Failed Configurations log.

## Self-heal
- Hints have no effect: confirm they reached the ranks (MPICH_MPIIO_HINTS_DISPLAY=1 in the wrapper), then confirm the real aggregator count from the trace, then check whether the app writes in parallel at all.
- MPI events missing: check DFTRACER_MPI_ENABLE in dftracer_config.hpp and the MPI include path baked into libdftracer_core.so.

## Self-learn
- Append failed configurations (date, app, workload, filesystem, system, bottleneck, config, result, before, after, delta, root_cause, do_not_use_when) and newly confirmed hint sets per MPI version here.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_mpi via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (2026-07-08, Flash-X 384 ranks / 8 nodes, Lustre) cb_nodes=16 + CRAY_CB_NODES_MULTIPLIER=2 + 16 x 4 MB stripes: aggregators 2 -> 16, critical-path write 6.80 s -> 1.45 s, avg large write 1.05 -> 3.76 MB, top rank's write share 52% -> 6.8%.
- (2026-07-09, Tuolumne, Python 3.13 + cray-mpich 9.1.0) patched mpi4py wheel (patchelf RPATH + libmpi.so.12 symlink + MPI4PY_MPIABI=mpich) imports and runs.
- (undated, VAST NVMe on Tuolumne) romio_cb_write=enable: +58% write BW.
- (undated, ScaFFold 32 ranks) dataloader_num_workers > 0: POSIX I/O time 5666 s -> 801 s (-86%); the real fix behind barrier time.

## Source: dftracer-agents `software-mpi` (verbatim, headings demoted)
_Original description:_ > MPI and MPI-IO (ROMIO) optimization strategies, Cray MPICH environment variable wiring, flux proxy env propagation rules, and dftracer MPI tracing requirements. Load this skill for any MPI or collective I/O work.

Cross-references: [[dftracer-io-optimization]] [[dftracer-preload-run]] [[workload-ior]] [[software-hdf5]]

---

#### L2 Software — MPI-IO / ROMIO

Applies when bottleneck is `small_io_pct` or `rand_pct` high (metric: bandwidth or time).

##### Hints file approach

```bash
cat > <WS>/romio_hints.txt << 'EOF'
cb_buffer_size 67108864
romio_cb_read enable
romio_ds_read enable
romio_ds_write enable
cb_nodes <num_nodes>
EOF
export ROMIO_HINTS=<WS>/romio_hints.txt
```

##### Cray MPICH environment variable (preferred over hints file)

**Format:** `pathname_pattern:key=value:key=value` — colon-separated key=value pairs per pattern.
Multiple file patterns are comma-separated. Use `*` to match all files.

```bash
# Correct format — colons between key=value pairs:
export MPICH_MPIIO_HINTS="*:romio_cb_write=enable:cb_buffer_size=67108864:cb_nodes=16:romio_ds_write=disable:striping_factor=16:striping_unit=4194304"

# To display hints actually applied (set before run):
export MPICH_MPIIO_HINTS_DISPLAY=1
```

**NEVER pass via `--env` to `flux proxy flux run`** — colons and semicolons in the value
cause flux run to lose the binary argument entirely. Always use a wrapper script:

```bash
cat > wrapper.sh << 'EOF'
#!/bin/bash
export MPICH_MPIIO_HINTS="*:romio_cb_write=enable:cb_buffer_size=67108864:cb_nodes=16"
exec "$@"
EOF
chmod +x wrapper.sh
flux proxy $JOB flux run -N 2 -n 192 --env LD_LIBRARY_PATH=<libs> bash wrapper.sh /path/to/binary args
```

**How to discover available hints on a new Cray MPICH version:**

```bash
strings /opt/cray/pe/mpich/<version>/ofi/cray/<ver>/lib/libmpi_cray.so \
  | grep -E "^romio_|^cb_|^striping_|^ind_|^ds_" | sort -u
```

##### Cray MPICH 9.0.1 — confirmed available hints

Extracted from `libmpi_cray.so` on Tuolumne (cray-mpich/9.0.1, OFI path):

| Hint | Recommended value | Effect |
|------|------------------|--------|
| `romio_cb_write` | `enable` | Collective buffering for writes |
| `romio_cb_read` | `enable` | Collective buffering for reads (disable on VAST/NVMe) |
| `romio_ds_write` | `disable` | Data sieving writes (disable to force 2-phase I/O) |
| `romio_ds_read` | `disable` | Data sieving reads |
| `cb_buffer_size` | `67108864` | 64 MB collective buffer per aggregator |
| `cb_nodes` | `16` | Aggregator count (match Lustre stripe count) |
| `cb_config_list` | `*:1` | Explicit aggregator mapping |
| `striping_factor` | `16` | Lustre stripe count (match with `lfs getstripe`) |
| `striping_unit` | `4194304` | 4 MB stripe size (match Lustre layout) |
| `ind_rd_buffer_size` | `4194304` | Independent read buffer |
| `ind_wr_buffer_size` | `4194304` | Independent write buffer |
| `romio_lustre_cb_lock_ahead_write` | `enable` | Lock-ahead for collective writes on Lustre |
| `romio_lustre_cb_lock_ahead_read` | `enable` | Lock-ahead for collective reads on Lustre |
| `romio_lustre_cb_lock_ahead_num_extents` | `4` | Number of lock-ahead extents |
| `romio_no_indep_rw` | `true` | ❌ NOT SUPPORTED on cray-mpich 9.0.1 — hint silently dropped with "unrecognized value" warning |

##### cb_nodes guidance for Lustre + cray-mpich 9.0.1

Per-workload rules validated on Tuolumne lustre5 (28 OSTs), 2 nodes × 192 ranks:

| Workload type | cb_nodes rule | Rationale |
|---|---|---|
| Contiguous fixed-size writes | Do NOT set (use default=2) | Default aggregators work well; adding more aggregators doesn't improve throughput and can cause pwrite stalls |
| Variable-size writes (e.g. normal-dist) | Do NOT set (use default=2) | More aggregators fragment variable chunks → massive pwrite p95 regression (+2650%) |
| Reads (untested on lustre5) | 2× stripe_count recommended per literature | Follows user's 2× rule |

The user's rule (cb_nodes = 2× stripe_count) is theoretically correct but empirically neutral-or-worse on Tuolumne at the tested scale (DIM_1=16M, 4 TS, 192 ranks). The close overhead savings from more aggregators are cancelled by pwrite stalls caused by buffer fragmentation.

If cb_nodes is needed: test at each scale step (R11) before production. Values tested:
- cb_nodes=16 + cb_buffer_size + striping hints → segfault (see workload-h5bench SKILL.md)
- cb_nodes=32 alone (write, 16-OST) → neutral (open −49%, overall ±0%)
- cb_nodes=56 alone (ND, 28-OST) → neutral (close −96%, pwrite p95 +2650%)

##### Common ROMIO parameters (all MPI implementations)

| Parameter | Recommended value | Effect |
|-----------|------------------|--------|
| `cb_buffer_size` | `67108864` (64 MB) | Collective I/O buffer per aggregator |
| `romio_cb_read` | `enable` | Aggregate reads via cb (helps Lustre; hurts VAST — see below) |
| `romio_cb_write` | `enable` | Aggregate writes via cb (beneficial on most systems) |
| `romio_ds_read` | `enable` | Data sieving for reads |
| `romio_ds_write` | `enable` | Data sieving for writes (default; disabling is FATAL on VAST) |
| `cb_nodes` | `<num_nodes>` | Number of aggregator processes |

##### Storage-specific ROMIO guidance (check FS_TYPE before applying — see Step 8-PRE of [[dftracer-pipeline]])

See [[workload-ior]] for quantified results on VAST NVMe (Tuolumne):
- `romio_cb_write=enable` → **+58% write BW** (always beneficial)
- `romio_cb_read=enable` → **−70% read BW** on VAST (AVOID on NVMe)
- `romio_ds_write=disable` → **FATAL** on VAST (352→95 MiB/s write collapse)

General rule: collective read buffering helps on high-latency storage (Lustre,
spinning disk). It hurts on parallel NVMe where concurrent reads are cheap.

---

#### Forwarding Environment Variables to MPI Ranks

`mpirun` does **not** automatically forward shell environment. Export + `-x`:

```bash
export DFTRACER_ENABLE=1
export DFTRACER_INIT=PRELOAD
export DFTRACER_DATA_DIR=/tmp
export DFTRACER_LOG_FILE=/tmp/traces/myapp
export MPICH_MPIIO_HINTS="*:romio_cb_write=enable"
export LD_PRELOAD=<dftracer_lib>/libdftracer_preload.so

mpirun --allow-run-as-root -np 4 \
  -x DFTRACER_ENABLE \
  -x DFTRACER_INIT \
  -x DFTRACER_DATA_DIR \
  -x DFTRACER_LOG_FILE \
  -x MPICH_MPIIO_HINTS \
  -x LD_LIBRARY_PATH \
  -x LD_PRELOAD \
  ./my_app
```

---

#### Flux Proxy — Environment Variable Propagation

`flux proxy` does NOT export the current shell's environment to the broker.
Variables set after `flux alloc` or `flux proxy` are invisible to job tasks.

**Always use `--env` flags with `flux run`:**

```bash
flux proxy <JOBID> flux run \
  -N 2 -n 192 \
  --env MPICH_MPIIO_HINTS="*:romio_cb_write=enable" \
  --env DFTRACER_ENABLE=1 \
  --env DFTRACER_LOG_FILE=<prefix> \
  --env DFTRACER_DATA_DIR=all \
  --env DFTRACER_INC_METADATA=1 \
  --env DFTRACER_INIT=FUNCTION \
  --env LD_LIBRARY_PATH=<libs> \
  <command>
```

Do NOT rely on `export VAR=value` before `flux proxy` — it will NOT propagate.

---

#### MPI tracing in dftracer

dftracer must be built with MPI support to capture `MPI_File_write/read` events:

```bash
cmake -DDFTRACER_ENABLE_MPI=ON ...
# Verify:
grep DFTRACER_MPI_ENABLE <prefix>/include/dftracer/core/dftracer_config.hpp
# Expected: #define DFTRACER_MPI_ENABLE 1
```

Runtime: the MPI shared library at run time must match the version dftracer was
compiled against:
```bash
strings libdftracer_core.so | grep "openmpi/include"  # must match system mpi.h path
```

##### Cray PE / MPICH include path issue in clang_syntax_check

```
fatal error: mpi.h: No such file or directory
```

Cray PE `mpicc --showme:incdirs` outputs `-I/path` (with `-I` prefix) instead of
a plain path, so auto-detection fails. Always pass explicitly:

```python
clang_syntax_check(run_id=..., filepath=...,
  extra_include_dirs=[
    "/opt/cray/pe/mpich/<version>/ofi/cray/<ver>/include",
    "<ws>/venv/lib/python3.*/site-packages/dftracer/include"
  ])
```

Get the exact MPI path: `mpicc -show | grep -o '\-I[^ ]*' | head -1`

---

#### NUMA Memory Binding (MPI processes)

```bash
numactl --hardware   # check topology
numactl --cpunodebind=0 --membind=0 <run_command>   # pin to NUMA node (no persistent side effect)
# For MPI:
mpirun --map-by numa:pe=<cores_per_node>   # OpenMPI
```

---

#### Citation

**WisIO (Yildirim et al., ICS 2025)** — covers `small_io_pct`, `rand_pct`, `read_time`, `write_time`
URL: https://dl.acm.org/doi/10.1145/3721145.3730395

**Drishti (Bez et al., PDSW 2022)** — L1/L2/L3 suggestion model including collective I/O
URL: https://ieeexplore.ieee.org/document/10027503

#### Failed Configurations

Entries below were applied during optimization loops and caused regressions or had no effect.
Check this section before proposing any configuration for this workload/software/filesystem.

Format per entry:
  date, app, workload, filesystem, system, bottleneck,
  config_attempted, result, metrics_before, metrics_after, delta,
  root_cause, do_not_use_when

<!-- New failed-config entries are appended below by the optimization loop (Step 8d-iii-FAIL) -->

---

#### Cray MPICH: `cb_nodes` is accepted but IGNORED (2026-07-08, measured)

Setting `cb_nodes` via `MPICH_MPIIO_HINTS` (or a `ROMIO_HINTS` file) does **not**
by itself increase the number of MPI-IO collective-buffering aggregators on Cray
MPICH. `MPICH_MPIIO_HINTS_DISPLAY=1` will happily echo back `cb_nodes = 8`, while
the runtime keeps using only **2** aggregators.

**Do not trust the hints display — verify the real aggregator count from traces:**
count the distinct ranks that issue writes `>= 1 MB` (the collective-buffer
flushes). Tiny writes happen on every rank (logs), so counting "ranks that write"
is useless; count ranks doing *large* writes.

```bash
dftracer_view -d <split_dir> --query 'cat == "POSIX"' --stream --no-metadata \
  | python3 -c 'import sys,json;p=set()
for l in sys.stdin:
  if "\"name\":\"pwrite\"" not in l and "\"name\":\"write\"" not in l: continue
  e=json.loads(l); r=e.get("args",{}).get("ret",0)
  if isinstance(r,int) and r>=1048576: p.add(e["pid"])
print("aggregators:",len(p))'
```

**What actually raises the aggregator count:** the Cray-specific
`CRAY_CB_NODES_MULTIPLIER` env var (used together with `cb_nodes`), plus a Lustre
stripe count wide enough to absorb them.

Measured on Flash-X (384 ranks / 8 nodes, 18 checkpoints, ~6.7 GB, Lustre):

| Config | aggregators | critical-path write | avg large write |
| --- | --- | --- | --- |
| parallel HDF5, no hints | 2 | 6.80 s | 1.05 MB |
| `+ cb_nodes=8` (hint echoed, ignored) | 2 | 5.53 s | 1.05 MB |
| `+ cb_nodes=16` + `CRAY_CB_NODES_MULTIPLIER=2` + 16×4 MB stripes | **16** | **1.45 s** | **3.76 MB** |

Top-1 rank's share of write bytes fell 52% → 6.8% (balanced parallel I/O).

**Ordering matters:** collective-buffering hints are worthless until the
application actually performs parallel writes. If one rank holds ~all write
bytes, fix that first (see [[workload-flashx]] serial-HDF5 case) — hints cannot
parallelize a single writer.


#### mpi4py on Cray MPICH (Tuolumne, 2026-07-09)

**Symptom:** mpi4py generic PyPI wheel (`mpi4py>=4.0`) on Tuolumne with cray-mpich fails to import with:
```
RuntimeError: cannot load MPI library
  /..../libmpi.so.12: cannot open shared object file
```

**Root cause:** mpi4py manylinux wheel expects standard MPICH SONAME `libmpi.so.12`, but Cray PE provides `libmpi_cray.so.12`. Generic wheel built for GNU MPI wrappers; Cray's soname differs.

**Fix (working recipe for Python 3.13 + cray-mpich/9.1.0):**

1. Download and extract wheel manually (pip rename fails on NFS):
   ```bash
   pip download mpi4py --python-version 313 --no-deps -d $WS/tmp
   cd $WS/tmp && unzip -q mpi4py-4.1.2-cp313-cp313-manylinux1_x86_64.manylinux_2_5_x86_64.whl
   ```

2. Patch extension RPATH to find Cray MPI lib + venv lib for symlink:
   ```bash
   CRAY_MPI_LIB="/opt/cray/pe/mpich/9.1.0/ofi/crayclang/20.0/lib"
   VENV_LIB="$WS/venv/lib"
   patchelf --set-rpath "$VENV_LIB:$CRAY_MPI_LIB" \
     mpi4py/MPI.mpich.cpython-313-x86_64-linux-gnu.so
   ```

3. Create symlink to resolve SONAME mismatch:
   ```bash
   ln -sf "$CRAY_MPI_LIB/libmpi_cray.so.12" "$VENV_LIB/libmpi.so.12"
   ```

4. Re-zip and install with ABI env var:
   ```bash
   zip -q -r mpi4py-patched.whl mpi4py/ mpi4py-*.dist-info/
   export MPI4PY_MPIABI=mpich
   pip install --force-reinstall --no-deps mpi4py-patched.whl
   ```

5. Verify import succeeds:
   ```bash
   python -c "from mpi4py import MPI; print(MPI.Get_version())"
   ```

**Environment persistence:**
Record `MPI4PY_MPIABI=mpich` and updated `LD_LIBRARY_PATH` in the session env script so all downstream steps inherit them:
```bash
export MPI4PY_MPIABI=mpich
export LD_LIBRARY_PATH="$WS/venv/lib:/opt/cray/pe/mpich/9.1.0/ofi/crayclang/20.0/lib:${LD_LIBRARY_PATH}"
```

**Key caveat:** `--no-binary=mpi4py` does NOT work on Python 3.13 + NFS (build succeeds but pip atomic-rename to NFS fails; manual extraction avoids pip's rename).


#### MPI_Barrier that "dominates" is usually a load-imbalance SINK, not a cost

**Symptom.** `MPI_Barrier` is ~99% of all MPI time and looks like the top bottleneck.

**Root cause.** In a DL trainer whose checkpoint is already `world_rank == 0`-gated, the
barrier does not *cost* time — it *absorbs* whatever wait the slowest rank imposes
(dataloader stragglers, the serialized rank-0 save). It is where imbalance is billed.

**Diagnostic tell.** As you fix the real upstream problem, per-barrier MEAN duration goes
*up* while wall clock goes *down*. Measured on ScaFFold (32 ranks): mean barrier
262 ms -> 657 ms across variants while `total_train_time` fell 1.97 s -> 1.64 s.

**Fix.** Attack the upstream imbalance (e.g. `dataloader_num_workers > 0` for prefetch and
compute/IO overlap). Do not do "barrier surgery," and do not rank by barrier aggregate.
Rank by wall clock / FOM.

**Anti-pattern: "do-less" levers.** Raising `checkpoint_interval` writes fewer checkpoints,
so any speedup is partly from doing less work, not from going faster. Verify total bytes /
data volume is unchanged before crediting a speedup. On ScaFFold it was both inferior to the
overlap fix AND did not compound with it.

**Tool caveat.** `comparator` reported MPI_Barrier p50 pinned at 167.79 ms across every
variant — a fixed time-bucket artifact. Use mean/p95/p99 and wall clock, not barrier p50.

##### CORRECTION (measured at a realistic run length)

The section above was inferred from a run whose training phase was ~2 seconds. At a fixed
1200-epoch (~12 min) run on the same 32-rank ScaFFold workload, `MPI_Barrier` aggregate is
**16.8 s across 32 ranks against 749.9 s of training (~2%)** — it is not the top bottleneck at
all. The "barrier = 99% of MPI time / ~65% of wall" reading was an artifact: in a 2-second run,
startup, teardown, and the first-epoch stragglers dominate everything.

What survives, and is the durable lesson:

- **Never rank bottlenecks from a run that is too short.** Fix a time budget (>= ~10 min of
  training), calibrate the epoch count on the baseline, and hold it constant across variants.
- A barrier still *absorbs* upstream imbalance, so attack the upstream cause. On this workload
  the real cost was POSIX I/O time (5666 s -> 801 s, -86%), removed by dataloader prefetch
  (`dataloader_num_workers > 0`), not by barrier surgery.
- Barrier mean duration rising while wall time falls remains a valid tell that the barrier is
  a sink rather than a cost — but confirm the aggregate is actually a meaningful fraction of
  wall clock before acting on it.

#### Barrier-dominated benchmark harnesses: check the call site before proposing anything (2026-08-05)

Two independent workloads on the same Cray MPICH system have now shown `MPI_Barrier` time
that belongs to the BENCHMARK'S OWN TIMING HARNESS, not to the application's algorithm
(IOR's timing loop; RAJAPerf's `KernelBase::startTimer/stopTimer`). Before proposing any
communication fix for a barrier finding, `grep -rn MPI_Barrier` the source and classify each
call site as harness vs. algorithmic. Harness barriers are off-limits (reducing them changes
what is measured) and the only remaining lever is collective-algorithm selection.

`MPICH_SHARED_MEM_COLL_OPT=1` (node-local shared-memory collective algorithms) is the
standard env-var-only lever for that case — but it has already measured **no_change (-1.6%,
inside noise)** on this system for IOR's barrier/allreduce harness at 64 ranks/node
(`opt_kb`, `software/L2/tuolumne/ior/cray-mpich`). Propose it, but state up front that the
prior on this system is null; it is worth a slot only when the barrier bucket is large
(>= several % of wall time) AND ranks are densely packed per node so a node-local algorithm
has something to exploit. Citation for the mechanism: Thakur et al., IJHPCA 19(1) 2005,
https://doi.org/10.1177/1094342005051521; runtime algorithm selection modelling:
Nuriyev & Lastovetsky, https://arxiv.org/pdf/2004.11062v1.
