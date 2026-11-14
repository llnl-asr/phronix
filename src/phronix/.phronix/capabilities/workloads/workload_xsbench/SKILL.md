---
name: workload_xsbench
description: XSBench (ANL-CESAR Monte Carlo neutronics cross-section lookup proxy app) - which of its six variants to build, the plain-make MPI=yes recipe, the hot-loop annotation trap that silently makes the app ~20x slower, the #ifdef MPI INIT trap, run sizing and memory per rank, the INVALID CHECKSUM warning that is NOT an annotation defect, Variorum "gpu" power records, and the CUDA variant. Load for XSBench, "INVALID CHECKSUM", "use of undeclared identifier 'data_fn'", "You cannot define MPI".
---
Cross-references: [[system_tuolumne]], [[software_papi]], [[software_mpi]], [[tools_dftracer]], [[tools_dftracer_utils]], [[software_cupti]]

# workload_xsbench

XSBench is a small (6 C files, ~1500 LOC) proxy app for the continuous-energy macroscopic neutron cross-section lookup kernel
of Monte Carlo neutron transport. It is compute/memory-latency bound (a random-access gather over a large unionized energy
grid) and does essentially **no application I/O and almost no MPI**. Converted from dftracer-agents' `workload-xsbench` (see
also there: system-tuolumne for module order/PAPI/Flux, software-papi for counter budget and `multiplex: 0`,
dftracer-annotate-c for INIT/FINI placement, tools-dftracer for install source selection).
`workload_xsbench_recipe` renders the recipe; `workload_xsbench_check` rules on a proposed command list.

## Rules

### Variant selection
The repo root holds one self-contained directory per programming model, each with its own `Makefile` and no top-level build
system (so `session_detect` reports `build_tool: unknown`):

| Directory | Language | MPI | Notes |
| --- | --- | --- | --- |
| `openmp-threading` | C | **`MPI=yes` switch in the Makefile** | The default/reference CPU version. Pick this. |
| `openmp-offload` | C | no Makefile switch | OpenMP 4.5 GPU offload |
| `cuda` | CUDA | no Makefile switch | |
| `hip` | C++ | **no Makefile switch** | sources have `#ifdef MPI` guards but the Makefile never defines `-DMPI` or links MPI |
| `opencl`, `sycl` | C / C++ | no | |

**Choose `openmp-threading` for a CPU MPI+OpenMP session.** It is the only variant whose Makefile can turn MPI on without
editing it. The `hip` variant would need hand-added `-DMPI` plus MPI include/link flags on top of `hipcc`, so it is not a
"builds cleanly with little effort" alternative when MPI events are wanted.

Because each variant is a separate directory, `session_detect` finds `hip/` and `cuda/` in the tree and reports `hip: true` /
`hip_tracing_needed: true` even when you are building the CPU variant. It also reports `hdf5: true` purely from a **system**
`h5cc`: `hdf5_in_source` is `false` and XSBench uses no HDF5 at all. Pass `hip=False, hdf5=False` explicitly to
`session_install_dftracer`.

### Build
Plain GNU make, no configure step:
```bash
# after the site module load, per feedback-cc-cxx-mpi-selection
export CC=`which mpicc`
export CXX=`which mpic++`
cd <WS>/source/openmp-threading
make MPI=yes -j8
```
Two Makefile quirks worth knowing:
* `MPI=yes` **overrides `CC` to the bare string `mpicc`**, so `mpicc` must be on `PATH`; the full path you exported in `CC` is discarded.
* `-flto -fopenmp -DOPENMP` are added only if `$(CC)` contains the substring `gcc`, `clang`, or `intel`. On Cray PE the wrapper
  path contains **`crayclang`**, so the `clang` branch matches and OpenMP is enabled *before* `MPI=yes` rewrites `CC`. If you
  set `CC` to a path without one of those substrings you silently get a **serial, un-optimized** build. Always confirm
  `-fopenmp -DOPENMP` appears in the compile lines.

For the annotated build, pass the dftracer include/lib through the Makefile's own variables (no pkg-config integration):
```
make MPI=yes -j8 \
  CFLAGS="-std=gnu99 -Wall -O3 -fopenmp -DOPENMP -DMPI -I<dft>/include" \
  LDFLAGS="-lm -L<dft>/lib64 -ldftracer_core -Wl,-rpath,<dft>/lib64"
```
Overriding `CFLAGS` wholesale drops the `-flto` the Makefile would have added: harmless, and it keeps the annotated and
baseline objects comparable.

### Annotation scope
After `clang_annotate_project`, re-annotate `Simulation.c` with the per-lookup kernels excluded (see Constraints):
```
clang_annotate_file(
  filepath="source/openmp-threading/Simulation.c", language="c", is_entry=False,
  exclude_functions='["calculate_micro_xs","calculate_macro_xs","grid_search",
                      "grid_search_nuclide","pick_mat","fast_forward_LCG",
                      "LCG_random_double","quickSort_parallel_internal_i_d",
                      "quickSort_parallel_internal_d_i"]')
```
That leaves only the three outer drivers (`run_event_based_simulation`, `run_history_based_simulation`,
`run_event_based_simulation_optimization_1`), entered once per rank: exactly the spans you want. Restore the pristine file from
`source/` before re-annotating so macros are not inserted twice. The other files need no exclusions, but check that the `qsort`
comparators in `XSutils.c` (`NGP_compare`, `double_compare`) stay unannotated: they are O(n log n) hot too. The default cost
filter already skips them.

**Generalizable rule:** in any proxy app, after `clang_annotate_project`, list the functions it annotated and ask of each "how
many times is this called per run?". Anything on a per-element/per-iteration path must go in `exclude_functions`.

### `main()`'s dftracer macros (second annotation trap)
`Main.c` wraps `MPI_Init`/`MPI_Comm_rank` in `#ifdef MPI`. The annotator inserts `DFTRACER_C_INIT` + `FUNCTION_START`
immediately after the last statement it sees there, i.e. **inside the `#ifdef`**, while leaving the early-exit
`DFTRACER_C_FUNCTION_END()` on the `kernel_id` error path **outside** it. In a non-MPI build that is a hard compile error
(`use of undeclared identifier 'data_fn'`), and it makes all tracing conditional on MPI. Fix: move `INIT`/`START`/metadata out
of the `#ifdef MPI` (still *after* `MPI_Init`, which is required), and make the closing `END`/`FINI` unconditional, ahead of the
`#ifdef MPI ... MPI_Finalize() ... #endif` block. Also add `DFTRACER_C_FINI()` next to the `DFTRACER_C_FUNCTION_END()` the
annotator places before `exit(4)` in `io.c`'s `print_CLI_error()`: it is a real process exit path reached after `INIT`.

### Run sizing and CLI
```
./XSBench -m event -s large -l <lookups> -t <threads> -G unionized
```
* `-s large` = 355 nuclides, 4,012,565 unionized gridpoints, **~5.6 GB per rank**: budget memory per rank, not per node.
* Every MPI rank independently performs the full `-l` lookups (ranks are replicas; the only MPI is a final `MPI_Barrier` +
  `MPI_Reduce`), so wall time depends on `-l` and threads, **not** on rank count.
* Grid initialization is ~6-8 s of the run and is deliberately named `grid_init_do_not_profile`.
* Reference throughput on an AMD MI300A CPU side, 22 OpenMP threads/rank: **~4.0-5.1 M lookups/s per rank**. So
  `wall ~ 8 s + (lookups / 4.5e6)`. `-l 200000000` gives ~55 s of simulation.
* Full-feature dftracer tracing (PAPI at 100 ms + POSIX/STDIO/MPI interception) costs about **21 %** throughput
  (5.12 -> 4.04 M lookups/s per rank).

### Per-rank memory caps the CPU ppn ladder (ranks are full replicas)
`Mem Usage per MPI Rank (MB)` measured with the openmp-threading build (printed before allocation, so a 2 s `timeout` run on a
login node reads it):

| size | unionized | hash | nuclide |
|---|---|---|---|
| small | 241 | ~0.2 GB | ~0.2 GB |
| large | 5,649 | 198 | 184 |
| XL | 119,354 | 3,895 | 3,882 |
| XXL | 250,642 | 8,165 | 8,151 |

On a 515 GB node: XXL-unionized fits ppn 1 only, XL-unionized ppn <= 2, XXL-hash/nuclide ppn <= 32. Mark the rest `SKIPPED` in
the state file up front. On an H100 (80 GB) the GPU build fits XXL hash/nuclide (8.3 GB on the device) but not
XL/XXL-unionized. XL and XXL both exit 1 (no reference checksum).

### CUDA variant (NVIDIA, e.g. a genesis sweep on an H100 machine)
* **Upstream `cuda/Main.cu` has no MPI at all** (maps.sh: `app_mpi=0` for CUDA), although `io.cu`/`XSutils.cu` already carry
  `#ifdef MPI` reduce/timer code. For a multi-rank corpus add `MPI_Init/Comm_size/Comm_rank` after the declarations and
  `MPI_Finalize` before `return`, both under `#ifdef MPI`; ranks are independent replicas exactly as in openmp-threading.
* `-DMPI` with an MPICH-family MPI (MVAPICH2) **fails in `mpicxx.h`**: *"You cannot define MPI; that name is reserved for the
  MPI namespace"* (nvcc compiles as C++). Add **`-DMPICH_SKIP_MPICXX`** (and `-DOMPI_SKIP_MPICXX` for OpenMPI).
* Build: `make CC="nvcc -ccbin g++" CFLAGS="... -arch=sm_90 -DMPI -DMPICH_SKIP_MPICXX -I<mpi>/include -I<dft>/include"
  LDFLAGS="-lm -L<mpi>/lib -lmpi -L<dft>/lib64 -ldftracer_core -Xlinker -rpath ..."`.
* Annotate with `clang_annotate_file` on the `.cu` files (the tool parses them host-side with `-xcuda --cuda-host-only`; pass
  `--cuda-path=<toolkit>` and the `-D/-I` flags in `compile_flags`). `__global__`/`__device__` functions are skipped
  automatically; brace insertion is disabled for CUDA, and every braceless `return` in this app is inside device code or the
  excluded qsort comparators. Exclude `center_print, border_print, fancy_int, logo, double_compare, NGP_compare, rn_v,
  get_time`. Re-apply the `#ifdef MPI` INIT/FINI move and the `print_CLI_error` FINI by hand, exactly as for the CPU variant.
* **The CUDA variant only implements event mode** (`-m history` exits 1), and the reference checksum exists only for
  `-s small`/`-s large` at the default lookups: **XL always prints `INAVALID CHECKSUM` and exits 1** on a healthy run. Treat
  rc 1 as success only together with the `Verification checksum` marker.
* `-s XL -G unionized` does not fit an 80 GB H100 per rank (and is absent from the ice4hpc matrix GPU rows); sweep XL with
  `hash`/`nuclide` only.
* A full-feature 1-rank `-s small` run is ~5 s: per rank only ~12 `C_APP`, 3 `CUDA_KERNEL` (baseline kernel id 0),
  7 `CUDA_MEMCPY`, 2 `collective`.

## Constraints
- **Never annotate the per-lookup kernels.** `clang_annotate_project` instruments **every** non-trivial function, and in
  `Simulation.c` that includes `calculate_micro_xs, calculate_macro_xs, grid_search, grid_search_nuclide, pick_mat,
  fast_forward_LCG`. These are called **once per lookup: hundreds of millions to billions of times** (`calculate_micro_xs`
  runs once per lookup *per isotope in the material*). The AST cost heuristic cannot see call frequency, so it happily
  annotates them.
- **XSBench has no application I/O.** Every POSIX/STDIO event is process startup. Do not size an I/O study around it; use it
  for compute/memory and PAPI work.
- The recipe/check tools render and check text only; they never build or run.

## Corner cases
- **Hot-loop symptom:** the app appears to hang. A configuration that runs in ~18 s un-annotated did not finish in **380 s**
  annotated, *even with `DFTRACER_ENABLE=0`*: the per-call overhead alone is enough. With tracing on it would also produce a
  multi-gigabyte trace of pure noise. Root cause: function-level instrumentation inside a hundreds-of-millions-iteration hot
  loop. Exact fix: the `clang_annotate_file` call above.
- **`validate_annotations` false positive:** it reports `critical I/O flow not annotated ... calls: read` for
  `quickSort_parallel_i_d` / `quickSort_parallel_d_i`. Those functions do no I/O: the checker substring-matches `read` inside
  the parameter name **`numThreads`**. Ignore it; confirm with a word-boundary search for an actual `read(` call.
- **`INVALID CHECKSUM` is expected, and rc=1 with it.** XSBench only carries reference verification checksums for its canonical
  `-l` values. Any other `-l` prints `Verification checksum: <n> (WARNING - INVALID CHECKSUM!)` and `main` returns non-zero.
  **This is not an annotation defect.** Prove it the cheap way: run the *unmodified* binary with identical arguments and
  compare: a correct annotation reproduces the checksum **bit-for-bit** (observed: both binaries returned `437675` at
  `-l 200000000`, 8 ranks, 22 threads). Do that comparison before blaming instrumentation for any XSBench result difference.
- **Do not read `cat: "gpu"` as "GPU tracing worked."** Variorum emits a `gpu` power category on a **CPU-only** build too,
  because it samples the node's GPUs from outside the application via rocm_smi. Those are type-13 counter records named `power`
  carrying per-socket watts (`socket_N.GPU_N`), produced by `dftracer_service`, and they appear even when
  `DFTRACER_HIP_TRACING_ENABLE` is undefined. Real GPU *tracing* means `KERNEL_DISPATCH` / `MEMORY_COPY` / `HIP_RUNTIME_API`
  events in the **per-rank app** traces. Check which file the events came from before claiming GPU coverage.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_xsbench_check`, repair the proposed commands, then call `workload_xsbench_recipe` and the check again:
- `hot_kernels_excluded`: restore `Simulation.c` from `source/`, then `clang_annotate_file` with the exclude list.
- `mpi_yes`: `make MPI=yes -j8`. `openmp_flags`: keep `-fopenmp -DOPENMP` in an overridden CFLAGS.
- `no_hip_hdf5_install`: `session_install_dftracer(hip=False, hdf5=False)`.
- `mpich_skip_mpicxx`: add `-DMPICH_SKIP_MPICXX` (`-DOMPI_SKIP_MPICXX` for OpenMPI). `cuda_event_only`: `-m event`.
- `input` (inconclusive): pass the command list. The same failure twice stops the loop for the user.

## Self-heal
On a hang, compile error or odd result match it to Corner cases and LESSONS.md (`lesson_search` the error first); compare with
the unmodified binary before blaming annotation; if a rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: a new XSBench variant or machine recipe verified by hand is added here
(`capability_update`); new software met becomes `software_<x>`; each error -> cause -> fix goes to LESSONS.md, each verified
recipe to WORKED.md.

## What works
- What a full-feature trace actually contains (2 nodes x 4 ranks x 22 threads, `-s large -l 200000000`, FUNCTION mode, with
  `dftracer_service` node counters and Variorum):

  | Layer | Present | Notes |
  | --- | --- | --- |
  | `C_APP` | yes (~10/rank) | one span per outer function; tiny by design |
  | `STDIO`, `POSIX` | yes (thousands) | **none of it is XSBench's own I/O**: loader/libc startup (`/proc/<pid>/maps`, `fgets`, `access`). XSBench reads no input deck. |
  | `collective` | yes, exactly 2/rank | `MPI_Barrier` + `MPI_Reduce`. No p2p and no other collective anywhere in the app. |
  | `papi` | yes | one type-11 record per sample interval per rank |
  | `sys` / `io` / `net` | yes | from `dftracer_service`, per node, type 7 |
  | `gpu` power (type 13) | yes | Variorum **node power telemetry, NOT GPU tracing** |
  | `KERNEL_DISPATCH` / `MEMORY_COPY` | no | CPU variant has no GPU work |
- Annotated openmp-threading run reproduces the checksum bit-for-bit (`437675` at `-l 200000000`, 8 ranks, 22 threads).
- CUDA variant on H100: 1-rank `-s small` full-feature run ~5 s with the nvcc build line above.
