---
name: workload_amg2023
description: AMG2023 (LLNL/AMG2023) hypre-based algebraic multigrid benchmark - single-file C driver, hypre >= 2.27 built in the session, CPU MPI+OpenMP CMake build, why only 3 functions are annotatable, INIT/FINI around hypre_MPI_Init/Finalize, -ldftracer_core, weak-scaling run sizing and the measured full-feature event inventory on Tuolumne. Load for any AMG2023 build, annotation or trace session; "Invalid number of processors or processor topology".
---
Cross-references: [[system_tuolumne]], [[software_papi]], [[software_cmake]], [[software_hypre]], [[tools_dftracer]], [[software_flux]], [[dftracer_annotate]], [[workload_amg]]

# workload_amg2023

AMG2023 (`LLNL/AMG2023`, LLNL-CODE-846758): parallel algebraic-multigrid benchmark, a thin driver over hypre (one 3079-line C
file, `amg.c`; the science lives in `libHYPRE`). Converted from dftracer-agents' `workload-amg2023` skill (its Related line:
system-tuolumne, software-papi, tools-dftracer, dftracer-annotate-c, software-cmake). `workload_amg2023_recipe` renders the
recipe; `workload_amg2023_check` rules on a command list. The full measured reference of the source skill follows the
standard sections, unchanged.

## Rules
- Build hypre >= 2.27.0 (v2.32.0) into the session workspace with `--with-MPI --with-openmp --enable-shared`; never a
  system/Cray hypre; verify `HYPRE_config.h` (OPENMP 1, SEQUENTIAL undef, HIP/CUDA undef) instead of trusting configure's rc.
- Build AMG2023 with CMake out-of-source: `-DCMAKE_BUILD_TYPE=Release -DHYPRE_PREFIX=<hypre> -DAMG_WITH_MPI=TRUE -DAMG_WITH_OMP=TRUE`
  (not the hand-edited Makefile).
- Link `-ldftracer_core` (patch the `-ldftracer` that `session_patch_build` injects).
- Annotate `main`, `BuildIJLaplacian27pt`, `BuildIJLaplacian7pt`; not `hypre_map27`, never hypre. 3 annotated + 1
  cost-filtered is correct (zero would be the red flag).
- In `main`: `DFTRACER_C_INIT` right after `hypre_MPI_Init`, `END` + `FINI` before `hypre_MPI_Finalize`; END+FINI on all five
  exits; FINI on both `BuildIJLaplacian*` `exit(1)` topology checks.
- `-P p q r` must multiply to the rank count; `-n` is per rank (weak scaling). For a 1-3 min window use `-n 240 240 240` at 16 ranks.

## Constraints
- Verify the two annotation defects on every run (no INIT/FINI inserted; END placed after `hypre_MPI_Finalize`):
  `clang_lint_annotations`' L3 rule only matches the literal `MPI_Finalize`.
- Read PAPI `multiplex` from the trace of the run you care about (0 on compute nodes, 1 on a login node for the same request).

## Corner cases
- Entry-point pass did not fire, likely because the signature is split as `hypre_int\nmain( hypre_int argc,` (non-`int` return).
- `LINKER_LANGUAGE CXX` although pure C (links through `mpic++`); `AMG_WITH_OMP=TRUE` -> `-openmp` + `libcraymp.so` under CCE (expected).
- Expected-absent layers: GPU `KERNEL_DISPATCH`/`MEMORY_COPY` (CPU build), `HDF5` (none; dftracer built with
  `DFTRACER_ENABLE_HDF5=OFF`), CPU/RAPL power (MSR denied to non-root on Tuolumne). The `gpu` category present is variorum node power.
- Runtime is startup-dominated at small sizes (n 90 -> 150 = 4.6x unknowns for 1.55x wall).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_amg2023_check`, repair the input, then recipe and check again:
- `use_cmake_not_makefile` / `out_of_source` / `hypre_prefix`: use the recipe's `cmake -S <src> -B <build> ... -DHYPRE_PREFIX=...`.
- `hypre_version` / `hypre_openmp` / `verify_hypre_config`: clone v2.32.0, configure with `--with-openmp`, grep `HYPRE_config.h`.
- `link_core`: `-ldftracer_core`. `no_hypre_annotation` / `no_map27`: annotate only `amg.c`'s three functions.
- `p_matches_ranks`: pick `-P` with product = ranks. `input` (inconclusive): pass the commands. Same failure twice stops the loop.

## Self-heal
On a failed build or run, match the error to Corner cases and LESSONS.md (`lesson_search` first), apply the fix, rerun; if a
rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: newly verified AMG2023 procedures (GPU hypre build, other problems) are added here
with `capability_update`, hypre itself becomes `software_hypre` if explored; errors go to LESSONS.md, verified recipes to WORKED.md.

## What works
- 2026-08-31, Tuolumne MI300A, CPU MPI+OpenMP build, dftracer FUNCTION mode + PAPI + variorum + node service, 2 nodes x 8 ranks
  `-n 240`: 16/16 rank traces + 2/2 service traces, none zero-byte, rc=0; 20,597,216 app events (p2p 20,366,777; C_APP 32 = 2/rank)
  and 40,108 service events; all four PAPI presets with `_delta`.

# Reference (verbatim from dftracer-agents' workload-amg2023 skill)

AMG2023 (`LLNL/AMG2023`, LLNL-CODE-846758) is a parallel algebraic-multigrid
benchmark. It is a **thin driver over hypre** — the entire benchmark is one
3079-line C file, `amg.c`, and all the science lives in `libHYPRE`.

## Reference: Shape of the code (matters for annotation)

`amg.c` contains exactly **four** function definitions:

| function | annotate? |
| --- | --- |
| `main` | yes |
| `BuildIJLaplacian27pt` | yes |
| `BuildIJLaplacian7pt` | yes (but only called for other problem ids) |
| `hypre_map27` | **no** — a 6-line index mapper called from the innermost assembly loop |

So a correct full-project annotation yields **3 functions annotated, 1
cost-filtered** — `clang_annotate_project` reports exactly that. Three
functions is NOT a red flag here (contrast
[[bug-clang-annotator-silent-zero-functions]]); *zero* would be. At run time
with `-problem 1` you get **2 `C_APP` events per rank** (`main` +
`BuildIJLaplacian27pt`), because the 7pt builder is not called.

**Do NOT annotate hypre.** It is ~800 C files whose kernels sit in the
innermost loops of the multigrid V-cycle and run O(10^9) times per solve;
annotating them would dominate both runtime and trace volume. hypre is a
dependency, not the app. The MPI/POSIX/STDIO layers of the trace already
capture hypre's behaviour through brahma interception — in the measured run
below, hypre's MPI traffic alone produced **20.4 M p2p events** with zero
hypre annotation.

## Reference: Build

AMG2023 needs hypre >= 2.27.0 built first. Build it into the session
workspace; never rely on a system/Cray hypre.

```bash
git clone --depth 1 --branch v2.32.0 https://github.com/hypre-space/hypre.git $WS/hypre-src
cd $WS/hypre-src/src
./configure --prefix=$WS/hypre --with-MPI --with-openmp --enable-shared CC="$CC" CXX="$CXX"
make -j 8 && make install
```

Verify the config actually took, rather than trusting configure's exit code:

```bash
grep -E 'HYPRE_USING_(OPENMP|HIP|CUDA)|HYPRE_SEQUENTIAL|HYPRE_RELEASE_VERSION' $WS/hypre/include/HYPRE_config.h
# want: HYPRE_USING_OPENMP 1, HYPRE_SEQUENTIAL undef, HYPRE_USING_HIP/CUDA undef
```

AMG2023 itself has both a hand-edited `Makefile` (whose `HYPRE_DIR` is
hardcoded to someone's home directory) and a CMake build. **Use CMake** —
the Makefile also unconditionally links CUDA and Umpire paths that do not
exist on most machines.

```bash
cmake $WS/source -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
  -DHYPRE_PREFIX="$WS/hypre" -DAMG_WITH_MPI=TRUE -DAMG_WITH_OMP=TRUE
```

Notes:
- `CMakeLists.txt` refuses an in-source build; always configure out-of-source.
- It sets `LINKER_LANGUAGE CXX` even though the code is pure C, so the link
  step runs through `mpic++`.
- `AMG_WITH_OMP=TRUE` resolves to `-openmp` under Cray CCE and pulls in
  `libcraymp.so` — expected, not an error.

## Reference: Running

`-P p q r` is the process topology and `-n nx ny nz` is the grid **per rank**;
`p*q*r` must equal the rank count or the app prints
`Error: Invalid number of processors or processor topology` and calls `exit(1)`.
Because the per-rank size is fixed, this is a **weak-scaling** benchmark: the
Figure of Merit stays roughly constant as you add ranks.

Runtime is heavily **startup-dominated** at small sizes. Measured at 2 nodes x
8 ranks on Tuolumne (MI300A, CPU-only build):

| `-n` per rank | wall time |
| --- | --- |
| 90  | 17.6 s |
| 150 | 27.3 s |
| 240 | 70.8 s |

So to land a run in a 1-3 minute window, use `-n 240 240 240` at 16 ranks;
raising `-n` from 90 to 150 (4.6x the unknowns) only bought 1.55x the wall
time.

## Reference: Annotation caveats (found 2026-08-31)

`clang_annotate_project` got the function selection right but produced two
defects that had to be fixed by hand — **verify these on every AMG2023 run**:

1. **No `DFTRACER_C_INIT` / `DFTRACER_C_FINI` were inserted at all.** The
   entry-point pass did not fire, even though `main` was annotated with
   `FUNCTION_START`. Without `INIT` the logger never initialises. Likely
   because the signature is split across lines as
   `hypre_int\nmain( hypre_int argc,` with a non-`int` return type.
2. **`DFTRACER_C_FUNCTION_END()` was placed AFTER `hypre_MPI_Finalize()`.**
   `clang_lint_annotations` did not catch it, because its L3 rule looks for
   the literal `MPI_Finalize` and hypre spells it `hypre_MPI_Finalize`.
   Every MPI-wrapping library with a prefixed finalize has this blind spot.

Correct layout for `main`:

```c
   hypre_MPI_Init(&argc, &argv);
   DFTRACER_C_INIT(NULL, NULL, NULL);
   DFTRACER_C_FUNCTION_START();
   DFTRACER_C_FUNCTION_UPDATE_STR("comp", "cpu");
   ...
   DFTRACER_C_FUNCTION_END();
   DFTRACER_C_FINI();
   /* Finalize MPI */
   hypre_MPI_Finalize();
   return (0);
```

`main` has **five** exit paths that all need `END` + `FINI`: the usage-print
`exit(1)`, two `return (-1)` precond-check paths, and the normal `return (0)`.
Both `BuildIJLaplacian*` functions also carry their own `exit(1)` topology
check, which terminates the process bypassing `main`'s FINI — so they need
`FINI` too.

Also note `session_patch_build` links **`-ldftracer`**, which does not exist;
the FUNCTION-mode library is **`libdftracer_core.so`**. Patch the injected
`target_link_libraries` to `-ldftracer_core` or the annotated build fails to
link. See [[bug-session-patch-build-wrong-dftracer-libname]].

## Reference: Measured full-feature event inventory (Tuolumne, 2 nodes x 8 ranks, `-n 240`)

CPU MPI+OpenMP build, dftracer FUNCTION mode, PAPI + variorum + node service.
16/16 rank traces and 2/2 service traces, none zero-byte, app rc=0.

App (per-rank) traces — 20,597,216 events over 16 pids:

| category | count | note |
| --- | --- | --- |
| `p2p` | 20,366,777 | `MPI_Iprobe` 9.99M, `MPI_Testall` 6.00M, `MPI_Test` 3.97M — hypre's async assembly polls hard |
| `comm` | 87,785 | `MPI_Comm_rank`/`MPI_Comm_size` |
| `STDIO` | 66,540 | `fgets`/`fopen`/`fclose` — almost all `/proc` and `/sys` reads, not app I/O |
| `dftracer` | 29,632 | internal (FH/CM/SH/HH) |
| `POSIX` | 22,624 | `access` 22,208 |
| `env` | 9,979 | `MPI_Get_count`, `MPI_Wtime` |
| `papi` | 8,733 | see below |
| `collective` | 5,114 | `MPI_Allreduce` 3,584, `MPI_Bcast` 928, `MPI_Scan` 416 |
| `C_APP` | 32 | exactly 2/rank: `main`, `BuildIJLaplacian27pt` |

Service (per-node) traces — 40,108 events, 2 files:

| category | count | note |
| --- | --- | --- |
| `sys` | 28,712 | per-core utilisation, `cpu` + `cpu-0`..`cpu-95`, 148 samples each |
| `io` | 10,360 | node-level I/O counters |
| `net` | 888 | node-level network counters |
| `gpu` | 148 | **variorum type-13 power**, keys `socket_0.GPU_0`..`socket_3.GPU_3`, `num_gpus_per_socket` |

`type` field: app traces are type 10 (p2p), 3, 1, 11 (papi), 2; service traces
are type 7 (counters) plus **type 13** (variorum power).

### PAPI

All four requested presets landed, each with a `_delta` companion:
`PAPI_TOT_CYC`, `PAPI_TOT_INS`, `PAPI_FP_OPS`, `PAPI_FP_INS` (8,733 each).

**`multiplex` is context-dependent**: `multiplex=0` on the compute nodes
(the 4 presets fit inside the 5 hardware counters natively), but the same
4-counter request on a **login node** reported `multiplex=1`. Always read
`multiplex` from the trace of the run you actually care about — do not infer
it from a probe run on a different node type. See [[software-papi]].

### Expected-absent layers on this build

- **GPU `KERNEL_DISPATCH` / `MEMORY_COPY`** — absent by design: this is a CPU
  build (`hypre` without `--with-hip`, `DFTRACER_HIP_TRACING_ENABLE` undef).
  Not a defect. The `gpu` category that *is* present is variorum node power,
  which is a different thing entirely.
- **`HDF5`** — absent; AMG2023 does no HDF5 I/O and dftracer was built with
  `DFTRACER_ENABLE_HDF5=OFF`.
- **CPU/RAPL power domains** — variorum reports only the AMD GPU domain.
  MSR/RAPL access is denied to non-root on Tuolumne (see [[system-tuolumne]]).

## Reference: Related

[[system-tuolumne]] · [[software-papi]] · [[tools-dftracer]] ·
[[dftracer-annotate-c]] · [[software-cmake]]
