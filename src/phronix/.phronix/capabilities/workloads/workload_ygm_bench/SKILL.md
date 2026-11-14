---
name: workload_ygm_bench
description: ygm-bench (github.com/llnl/ygm-bench) - build against an annotated YGM tree (FETCHCONTENT_SOURCE_DIR_YGM), the hot-loop over-annotation/selective-aggregation fix, MPI_Iallreduce rank-density collapse, irecv buffer OOM tuning (YGM_COMM_IRECV_SIZE_KB), and the confirmed >=10-minute scaled dftracer run configuration on Tuolumne. Load whenever running or tracing ygm-bench (YGM itself is software_ygm); around_the_world_ygm, barrier_bench, MAX_WAITSOME_IALLREDUCE, OOM at 96 ranks/node.
---
Cross-references: [[software_ygm]], [[dftracer_annotate_cpp]], [[system_tuolumne]], [[tools_dftracer]], [[software_mpi]], [[workload_ior]], [[workload_h5bench]], [[software_flux]]

# workload_ygm_bench

`ygm-bench` is the traced BENCHMARK/workload here, the same role IOR or h5bench play for their libraries (see [[workload_ior]] /
[[workload_h5bench]] for the analogous pattern). [[software_ygm]] is the library it exercises and is annotated by dftracer; this
capability is about building, scaling and running the benchmark, not YGM's own annotation/build internals. Converted from
dftracer-agents' `workload-ygm-bench` skill (lesson cross-references there point to `dftracer-annotation-lessons` LESSONS_LOG.md
2026-08-04 and CP10, now in the dftracer annotate capabilities). `workload_ygm_bench_recipe` renders the recipe,
`workload_ygm_bench_check` rules on a command list.

## Rules
### Build: against THIS session's annotated YGM (not a fresh copy)
- `ygm-bench`'s `CMakeLists.txt` tries `find_package(ygm CONFIG)` first, falling back to `FetchContent_Declare(ygm GIT_REPOSITORY ...)`.
  The annotated YGM tree has no `install()`/`export()` rules, so `find_package` never succeeds: it would silently fall through to
  fetching a FRESH, UNANNOTATED ygm from GitHub. Configure ygm-bench with `-DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source`,
  which makes `FetchContent_MakeAvailable(ygm)` use the local annotated tree in place instead of git-cloning: no CMakeLists.txt
  patch needed in either repo. The general FETCHCONTENT_SOURCE_DIR_<NAME> pattern applies beyond YGM (dftracer-annotation-lessons
  LESSONS_LOG.md 2026-08-04).
- Annotated YGM's own `CMakeLists.txt` links its `dftracer_core_imported` target into the `ygm` INTERFACE target, so ygm-bench's
  `target_link_libraries(... ygm::ygm)` transitively picks up the dftracer link: confirm with `ldd <binary> | grep dftracer`.
- ygm-bench's benchmark entry points (`around_the_world_ygm.cpp`, `barrier_bench.cpp`, ...) each need their own explicit
  `DFTRACER_CPP_INIT()`/`DFTRACER_CPP_FINI()` in `main()`: without it every `DFTRACER_CPP_FUNCTION()` reached transitively through
  YGM is a silent no-op because dftracer was never initialized in that process. A header-only library's internal annotation is
  never self-sufficient: every CONSUMING application needs its own INIT/FINI too.
- The prerelease wheel (see [[tools_dftracer]]) does not ship `dftracer_service`: if the node-counter daemon is required, install a
  second from-source dftracer for that binary while still linking the app against whichever dftracer install matches its own
  compiler ABI.

### Run: selective aggregation for the hot progress loop (critical, 2026-08-04)
- The initial annotation pass instrumented `ygm::comm::local_progress()` and 8 sibling functions on YGM's async progress-polling
  path (dftracer-annotation-lessons CP10): `local_progress`, `local_wait_until`, `process_receive_queue`, `flush_next_send`,
  `check_completed_sends`, `check_if_production_halt_required`, `post_new_irecv`, `local_process_incoming`,
  `handle_completed_send`, all reachable from one shared progress-poll path. At 128-rank scale (`around_the_world_ygm`) traced runs
  were 5-10x+ slower than untraced, with wall time independent of `-n`: tracing overhead, not the communication pattern, dominated.
- **Final fix used (not a full strip): DFTRACER selective aggregation.** Keep all 9 functions annotated and, when RUNNING ygm-bench:
  ```bash
  export DFTRACER_ENABLE_AGGREGATION=1
  export DFTRACER_AGGREGATION_TYPE=SELECTIVE
  export DFTRACER_AGGREGATION_FILE=<path-to-rules.yaml>
  export DFTRACER_TRACE_INTERVAL_MS=5000
  ```
  `rules.yaml`:
  ```yaml
  inclusion:
    - "dur < 1000"
  exclusion: []
  ```
  (full rule syntax: dftracer-annotation-lessons CP10). This restored near-linear scaling AND kept per-function visibility (real
  `dft_cnt` call counts on aggregated `CPP_APP` events) at a fraction of the trace volume: the final 128-rank/11-min run
  (`-n 5600`, 716,800 hops) produced ~55MB across 128 rank files, vs >1GB PER RANK in the earlier unaggregated attempt. Don't default
  to stripping annotation from a traced benchmark's hot path: aggregation is almost always the better tradeoff when the hot
  function's own behavior is diagnostically relevant.

### Reference config for any >=10-minute scaled ygm-bench dftracer run on Tuolumne (2026-08-04)
- 4 nodes, 32 ranks/node (NOT 96: Iallreduce collapse + OOM risk)
- default YGM buffer settings (`YGM_COMM_NUM_IRECVS`/`YGM_COMM_IRECV_SIZE_KB` unset)
- selective aggregation enabled as above
- `-n` sized ~5000-5600 for ~10-11 minutes at this scale; scales roughly linearly with `-n` once aggregation is enabled
  (n=500 -> 70.2s, n=5000 -> 572s, n=5600 -> 660s at the same 128-rank config)

## Constraints
- **MPI_Iallreduce collapses badly at high per-node rank density (Cray MPICH, Tuolumne).** `around_the_world_ygm`'s
  termination-detection protocol issues thousands of `MPI_Iallreduce` calls. Measured with `DFTRACER_ENABLE=0` (untraced, so a
  real MPI/system finding, not a tracing artifact): 4 ranks/1 node: 510K hops/sec; 32 ranks/1 node: 1,229 hops/sec (~400x
  collapse), `MAX_WAITSOME_IALLREDUCE` = 130.2s of 130.1s total wall time (essentially ALL time is collective wait). Per-node rank
  density is a first-order performance variable for ygm-bench (and likely any workload with a similar Iallreduce-heavy termination
  protocol) on Tuolumne's Cray MPICH: don't assume "more ranks = proportionally more work done." 32 ranks/node was usable; 96
  ranks/node combined with this collapse made runs take tens of minutes even for modest workloads (separately from the OOM risk).
- **irecv buffer memory.** Default `YGM_COMM_NUM_IRECVS=8` x default irecv size (1GB) = 8GB/rank of receive buffers. At 96
  ranks/node that's ~768GB, causing OOM (`memory.peak ~ 476.87G`, consistently hit across nodes/attempts: same cgroup memory
  ceiling every time). 32 ranks/node with DEFAULT buffers (1GBx8=8GB/rank x32=256GB/node) worked reliably, no OOM, no hang.
- The recipe/check tools render and check text only.

## Corner cases
- Cutting the buffer size must use the CORRECT variable name: **`YGM_COMM_IRECV_SIZE_KB`** (singular "IRECV"), NOT
  `YGM_COMM_IRECVS_SIZE_KB` (plural), which is only the JSON output's display label (`comm_environment.hpp` line ~169), not what
  `std::getenv` reads (line ~112). The wrong (plural) name silently no-ops and the default 1GB/irecv stays.
- A too-small value (tested 64MB) at 96 ranks/node avoided the OOM but produced what LOOKED like a deadlock: low memory use
  (`flux exec free -g` ~6GB/501GB used) and no progress for minutes; likely the same Iallreduce collapse taken further, not a true
  deadlock (not fully confirmed given time constraints).
- `DFTRACER_CPP_FUNCTION` events missing from the bench -> the entry point lacks its own INIT/FINI.
- ygm-bench linked against an unannotated YGM -> FETCHCONTENT_SOURCE_DIR_YGM not set; check `ldd <binary> | grep dftracer`.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_ygm_bench_check`, repair the proposed commands, then call `workload_ygm_bench_recipe` and the check again:
- `fetchcontent_annotated`: add `-DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source` to the ygm-bench configure.
- `irecv_env_name`: use `YGM_COMM_IRECV_SIZE_KB` (singular), or keep defaults at 32 ranks/node.
- `rank_density`: 32 ranks/node (reference 4 nodes x 32).
- `selective_aggregation` / `aggregation_file`: export the four aggregation variables with a rules.yaml (`inclusion: ["dur < 1000"]`).
- `input` (inconclusive): pass the command list. The same failure twice stops the loop for the user.

## Self-heal
On a failed or slow run, match the symptom to Constraints/Corner cases and LESSONS.md (`lesson_search` first); if the recipe or a
rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: another benchmark entry point, scale or system verified by hand is added here
(`capability_update`); YGM-library facts go to [[software_ygm]]. Each new error -> cause -> fix goes to LESSONS.md, each verified
recipe to WORKED.md.

## What works
- Small run (GNU toolchain, 1 node / 4 ranks): `around_the_world_ygm -n 50 -t 2 -p` and `barrier_bench -b 500 -a 0 -t 2 -p`.
  Trace category breakdown (one representative rank file, 8,222 events): `CPP_APP` 3686 (annotated comm functions), `p2p` 3361
  (`MPI_Testsome`/`MPI_Test`/`MPI_Irecv`/`MPI_Isend`), `env` 772, `collective` 264 (`MPI_Iallreduce`/`MPI_Allreduce`), `POSIX` 69,
  `dftracer`(meta) 32, `STDIO` 22, `comm` 16: real annotated comm/collective activity dominates, not init/POSIX noise.
- Scaled run (2026-08-04): `ygm-bench/src/around_the_world_ygm -n 5600 -t 1 -p`, 4 nodes x 32 ranks/node (128 total, GNU
  toolchain, single MPI runtime), full annotation + selective aggregation: 660.04s (11.0 min), 716,800 hops,
  `MAX_WAITSOME_IALLREDUCE`=646s (the Iallreduce collapse is the genuine bottleneck, not a tracing artifact), 55MB trace across 128
  rank files.
