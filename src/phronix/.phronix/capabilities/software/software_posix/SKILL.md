---
name: software_posix
description: POSIX I/O optimization by layer - L1 application (buffering/coalescing, access ordering, fd reuse, async I/O, stat caching), L2 software hints (posix_fadvise, MALLOC_ARENA_MAX, OMP/MKL threads), L3 OS/filesystem (Lustre lfs setstripe ONLY on Lustre, near-node flash / Rabbit, block-device readahead, vm dirty/page cache sysctls, I/O scheduler) - plus dftracer DFTRACER_DATA_DIR for capturing POSIX events and manual proposals for posix_*_ops_slope metrics. Load for any POSIX I/O bottleneck (small_io_pct, rand_pct, read/write_time_pct, metadata_time_pct, posix_*_ops_slope), on dftracer `Code 2001` with DFTRACER_DATA_DIR=all, `lfs` errors on non-Lustre mounts, or a 4x write regression from romio_ds_write=disable on VAST.
---
Cross-references: [[dftracer_optimize_io]] [[dftracer_trace]] [[software_mpi]] [[software_hdf5]] [[system_tuolumne_rabbit]] [[software_mpifileutils]] [[capability_builder]]

# software_posix

Converted from dftracer-agents skill `software-posix`. Tools: `software_posix_recipe` (predictor) and `software_posix_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- small_io_pct (bandwidth/iops): coalesce small reads via a staging buffer, batch writes into a pre-allocated buffer, readv/writev instead of read/write loops; Python: larger chunk_size, np.fromfile.
- rand_pct (bandwidth/time): read in file-offset order (sort indices), posix_fadvise(fd,0,0,POSIX_FADV_SEQUENTIAL), mmap for random access, DL: sort dataset by file size and shuffle only indices in memory.
- read_time_pct / write_time_pct (time): keep fds open across iterations, O_DIRECT when reuse is low, async I/O (io_uring; aiofiles/asyncio), fallocate before writing.
- metadata_time_pct (metadata_ops): cache stat(), open once per epoch not per sample, pre-built file lists instead of readdir loops, try/except instead of os.path.exists in hot loops.
- L2 per-process readahead (no sudo): posix_fadvise(fd,0,0,POSIX_FADV_SEQUENTIAL) and POSIX_FADV_WILLNEED before sequential reads.
- L2 env: MALLOC_ARENA_MAX=2 (glibc arena fragmentation), OMP_NUM_THREADS / MKL_NUM_THREADS = physical core count, HBWMALLOC_POLICY=transparent when high-bandwidth memory exists.
- L3 Lustre tuning (lfs setstripe -c/-S, lfs mkdir -c DNE) applies ONLY when FS_TYPE is lustre; on VAST, NFS, GPFS, BeeGFS or local filesystems lfs is a no-op or error. Always record the rollback (lfs setstripe -c 1 / -S 1m).
- Stripe count: N = OST count, capped at 8 for files < 1 GB, 16+ for large; stripe size 4 MB aligns to the ROMIO collective buffer. DNE (`lfs mkdir -c`) may require admin.
- `romio_ds_write=disable` is catastrophic on VAST NVMe (4x write regression).
- Near-node flash (network PFS): stage hot data onto node-local flash and copy outputs back; on Tuolumne Rabbit via Flux `-S "#DW jobdw type=<xfs|gfs2|lustre> ..."`, tier by sharing scope SHM -> XFS -> GFS2 -> Lustre (system_tuolumne_rabbit).
- Kernel readahead (`sudo blockdev --setra`, default 128 = 64 KB, recommended 4096-16384) applies ONLY to local_nvme / local_hdd and affects every process on the device; rollback `--setra 128`.
- VM/page cache (sudo): vm.dirty_ratio=20, vm.dirty_background_ratio=5, vm.dirty_expire_centisecs=3000, vm.dirty_writeback_centisecs=500; read-heavy vm.vfs_cache_pressure=50 (default 100).
- I/O scheduler (sudo): `none` for NVMe, `mq-deadline` for HDD; read the current value first and roll back to it.
- DFTRACER_DATA_DIR must be a real filesystem path (`/` for everything, `/tmp`, or colon-separated `/data:/scratch`). The string `all` is understood only by the Python helper layer and causes `Code 2001` at the C++ runtime.
- session_generate_optimization_proposals does not support posix_*_ops_slope metrics: derive proposals manually from the slope table.
- Check the Failed configurations log before proposing any configuration for this workload/software/filesystem.

## Constraints
- Sudo-only L3 changes (blockdev, sysctl, scheduler) are usually unavailable on shared HPC nodes; prefer L1/L2 and per-directory Lustre settings.
- Failed-config entries use: date, app, workload, filesystem, system, bottleneck, config_attempted, result, metrics_before, metrics_after, delta, root_cause, do_not_use_when.
- Citations: WisIO (Yildirim et al., ICS 2025, https://dl.acm.org/doi/10.1145/3721145.3730395); Drishti (Bez et al., PDSW 2022, https://ieeexplore.ieee.org/document/10027503).

## Corner cases
### dftracer `Code 2001` at startup with DFTRACER_DATA_DIR=all
Cause: `all` is a Python-helper alias, not understood by the C++ runtime. Fix: DFTRACER_DATA_DIR=/ (or the real data dirs, colon-separated).

### `lfs setstripe` errors or does nothing
Cause: the target is not on Lustre (VAST/NFS/GPFS/BeeGFS/local). Fix: skip Lustre L3 there; use filesystem-appropriate tuning.

### 4x write regression after romio_ds_write=disable
Cause: VAST NVMe. Fix: never disable data sieving writes on VAST.

### No proposals for posix_data/close/metadata/seek_ops_slope
Cause: session_generate_optimization_proposals lacks slope support. Fix: data -> larger transfers / ROMIO hints / stripe; close -> stagger closes / ind_wr_buffer_size / client cache; metadata -> shared file / pre-create / DNE; seek -> larger transfer + romio_cb_write=enable.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_posix_recipe` renders the recipe; validator `software_posix_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `data_dir_not_all` fails: DFTRACER_DATA_DIR=/ (or real colon-separated paths). Then render with `software_posix_recipe` and validate again.
- `lfs_only_on_lustre` fails: Skip Lustre L3 settings; use the tuning for the actual filesystem. Then render with `software_posix_recipe` and validate again.
- `no_ds_write_disable_vast` fails: Leave data-sieving writes at the default on VAST. Then render with `software_posix_recipe` and validate again.
- `readahead_only_local` fails: Use posix_fadvise (L2) or filesystem-level settings instead. Then render with `software_posix_recipe` and validate again.
- `preload_needs_data_dir` fails: export DFTRACER_DATA_DIR=/ (or the app's data directories). Then render with `software_posix_recipe` and validate again.

## Self-heal
- If a proposed L3 change targets the wrong filesystem type, re-detect FS_TYPE (df -T / lfs getstripe) and re-select the layer's options.

## Self-learn
- Append every regressing or no-effect POSIX configuration to the Failed configurations log with the full field set.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_posix via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, from the source skill) DFTRACER_DATA_DIR=/ captures all POSIX I/O; colon-separated real paths (e.g. /data:/scratch) restrict capture.

## Source: dftracer-agents `software-posix` (verbatim, headings demoted)
_Original description:_ > POSIX I/O optimization strategies: application-level buffering (L1), readahead and library hints (L2), OS/filesystem tuning (L3), and dftracer DATA_DIR configuration for capturing POSIX events. Load this skill for any POSIX I/O bottleneck work.

Cross-references: [[dftracer-io-optimization]] [[dftracer-preload-run]] [[software-mpi]] [[software-hdf5]]

---

#### L1 Application — POSIX I/O Strategies

##### Small I/O (`small_io_pct` high — metric: bandwidth or iops)

- Coalesce small reads into a single larger read with a staging buffer
- Replace per-element writes with batch writes to a pre-allocated buffer
- Use `readv`/`writev` (scatter/gather) instead of loops of `read`/`write`
- For Python: increase `chunk_size`; use `np.fromfile` over loops

##### Sequential access (`rand_pct` high — metric: bandwidth or time)

- Reorder access so items are read in file-offset order (sort indices before I/O)
- Add `posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL)` before sequential reads
- Use `mmap` for random access patterns to let the OS handle page faults
- For deep learning: sort dataset by file size, shuffle only indices in memory

##### Read/write time (`read_time_pct` or `write_time_pct` high — metric: time)

- Pre-open files and keep file descriptors open across iterations
- Use `O_DIRECT` for cache-bypassing when data reuse is low
- Add async I/O: `io_uring` (C/C++) or `aiofiles`/`asyncio` (Python)
- Pre-allocate file size with `fallocate` before writing to avoid fragmentation

##### Metadata time (`metadata_time_pct` high — metric: metadata_ops)

- Cache `stat()` results; avoid repeated `lstat`/`stat` on the same paths
- Open files once per epoch, not once per sample
- Replace `readdir()` loops with pre-built file-list caches
- For Python: replace `os.path.exists()` in hot loops with `try`/`except`

---

#### L2 Software — POSIX Readahead and Library Hints

##### Per-process readahead (no sudo)

```c
// Add to source before sequential reads:
posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);
posix_fadvise(fd, 0, 0, POSIX_FADV_WILLNEED);
```

##### General I/O library environment variables

```bash
# Reduce glibc arena fragmentation for I/O-heavy apps:
export MALLOC_ARENA_MAX=2

# OMP threading for I/O threads:
export OMP_NUM_THREADS=<physical_core_count>
export MKL_NUM_THREADS=<physical_core_count>

# High-bandwidth NUMA memory (when available):
export HBWMALLOC_POLICY=transparent
```

---

#### L3 OS/Filesystem — Lustre Parallel Filesystem (FS_TYPE: lustre ONLY)

**Do NOT apply these on VAST, NFS, GPFS, BeeGFS, or local filesystems.**
`lfs` commands are no-ops or errors on non-Lustre mounts.
`romio_ds_write=disable` is catastrophic on VAST NVMe (4× write regression).

These require no sudo (per-directory settings):

```bash
# Stripe count (N = OST count, capped at 8 for files < 1 GB; 16+ for large):
lfs setstripe -c <N> <WS>/traces/
# Rollback:
lfs setstripe -c 1 <WS>/traces/

# Stripe size (4 MB aligns to ROMIO collective buffer):
lfs setstripe -S 4m <WS>/traces/
# Rollback:
lfs setstripe -S 1m <WS>/traces/

# Per-file stripe before write:
lfs setstripe -c 4 -S 4m <WS>/traces/<file>
```

##### Lustre metadata (may require admin)

```bash
# Use DNE (Distributed Namespace) — admin-only:
lfs mkdir -c <N> <dir>
```

---

#### L3 OS/Filesystem — Near-Node Flash Accelerators (FS_TYPE: network PFS)

On systems with node-local NVMe accelerators, front the network PFS with a local
flash tier: stage hot data onto per-node/per-chassis flash, run against it, copy
persistent outputs back. No sudo — provisioned per job. On **Tuolumne (Rabbit)**
this is a Flux `-S "#DW jobdw type=<xfs|gfs2|lustre> ..."` directive; pick the
tier by sharing scope (SHM → XFS → GFS2 → Lustre). Full guide:
[[system-tuolumne-rabbit]].

---

#### L3 OS/Filesystem — Linux Kernel Readahead (FS_TYPE: local_nvme, local_hdd ONLY)

```bash
# Per-device (sudo required):
sudo blockdev --setra <KB> /dev/<dev>
# Default: 128 (64 KB); recommended: 4096–16384 (2–8 MB)
# Rollback:
sudo blockdev --setra 128 /dev/<dev>

# Check current:
blockdev --getra /dev/<dev>
```

Side effect: affects all processes reading from this device.

---

#### L3 OS/Filesystem — VM and Page Cache Tuning

```bash
# Flush dirty pages (sudo required):
sudo sysctl -w vm.dirty_ratio=20           # flush at 20% of RAM dirty
sudo sysctl -w vm.dirty_background_ratio=5 # start background flush at 5%
sudo sysctl -w vm.dirty_expire_centisecs=3000   # 30s dirty page lifetime
sudo sysctl -w vm.dirty_writeback_centisecs=500  # flush every 5s

# Read-heavy: reduce page cache reclaim:
sudo sysctl -w vm.vfs_cache_pressure=50    # default 100
```

---

#### L3 OS/Filesystem — I/O Scheduler

```bash
# Check current:
cat /sys/block/<dev>/queue/scheduler

# For NVMe (no scheduler overhead needed):
echo none | sudo tee /sys/block/<dev>/queue/scheduler

# For HDD:
echo mq-deadline | sudo tee /sys/block/<dev>/queue/scheduler

# Rollback:
echo <original> | sudo tee /sys/block/<dev>/queue/scheduler
```

---

#### dftracer POSIX Configuration

##### DFTRACER_DATA_DIR

Must be a **real filesystem path** (not the string `"all"` at the C++ layer):

| Goal | Value |
|------|-------|
| Capture all I/O on any file | `/` or leave empty → use `/` |
| Capture I/O under /tmp | `DFTRACER_DATA_DIR=/tmp` |
| Two data dirs | `DFTRACER_DATA_DIR=/data:/scratch` |

The string `"all"` is only understood by the Python helper layer and causes
`Code 2001` at the C++ runtime.

##### `posix_*_ops_slope` bottlenecks

`session_generate_optimization_proposals` does not support slope metrics.
Derive proposals manually:

| Metric | Cause | Fix |
|--------|-------|-----|
| `posix_data_ops_slope` | Bursty data I/O | Increase transfer size (L1); ROMIO hints (L2); stripe tuning (L3) |
| `posix_close_ops_slope` | Bursty close pattern | Stagger close timing (L1); `ind_wr_buffer_size` (L2); client cache (L3) |
| `posix_metadata_ops_slope` | Bursty metadata | Shared file instead of file-per-process (L1); pre-create (L2); DNE (L3) |
| `posix_seek_ops_slope` | Scattered seek+write | Larger transfer size + `romio_cb_write=enable` (see [[software-mpi]]) |

---

#### Bottleneck → Optimization Mapping

| Bottleneck | Primary fix | Layer |
|------------|------------|-------|
| `small_io_pct` | Buffer reads/writes | L1 |
| `rand_pct` / `seq_pct` low | Sort access order | L1 |
| `read_time_pct` | Async I/O, O_DIRECT | L1 / L2 |
| `write_time_pct` | Async write, fallocate | L1 / L2 |
| `metadata_time_pct` | Cache stat(), open once | L1 |
| `posix_seek_ops_slope` | ROMIO cb_write, larger -t | L2 |

Full bottleneck → optimization table: [[dftracer-io-optimization]]

---

#### Citations

**WisIO (Yildirim et al., ICS 2025)**
URL: https://dl.acm.org/doi/10.1145/3721145.3730395
Covers: small_io, rand/seq (sequentiality), read_time, write_time, metadata_time

**Drishti (Bez et al., PDSW 2022)**
URL: https://ieeexplore.ieee.org/document/10027503
Covers: small-io buffering, metadata caching, sequentiality hints

#### Failed Configurations

Entries below were applied during optimization loops and caused regressions or had no effect.
Check this section before proposing any configuration for this workload/software/filesystem.

Format per entry:
  date, app, workload, filesystem, system, bottleneck,
  config_attempted, result, metrics_before, metrics_after, delta,
  root_cause, do_not_use_when

<!-- New failed-config entries are appended below by the optimization loop (Step 8d-iii-FAIL) -->
