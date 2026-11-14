---
name: workload_lammps_kokkos
description: LAMMPS + KOKKOS/HIP on AMD MI300A (Cray PE, Flux, ROCm 7.x): elcapitan_kokkos preset, Cray GTL vs ROCm libamdhip64 soname mismatch, HSA_XNACK/MPICH_GPU_SUPPORT_ENABLED, -k on g 1, dftracer finalize() symbol collision in main.cpp (0-byte traces), 50-file annotation scope, device-code and include-placement annotator defects, lattice2box/create_atom event blowup. Load for lammps, kokkos HIP, 'libamdhip64.so.6', 'cxil_map: write error', 'static declaration of finalize'.
---
Cross-references: [[software_rocm]], [[software_papi]], [[software_cmake]], [[software_mpi]], [[software_flux]], [[system_tuolumne]], [[tools_dftracer]]

# workload_lammps_kokkos

Converted from dftracer-agents' `workload-lammps-kokkos` skill (all of its content is under Rules, verbatim with headings demoted).
`workload_lammps_kokkos_recipe` renders the recipe the skill knows as JSON (predictor); `workload_lammps_kokkos_check` rules on a proposed recipe or command list (validator).

## Rules

### workload-lammps-kokkos

LAMMPS + KOKKOS/HIP on Tuolumne-class MI300A (Cray PE, Flux, ROCm 7.x).

#### Build

Use the upstream **`cmake/presets/elcapitan_kokkos.cmake`** preset — El Capitan is the
same MI300A APU hardware. It sets `Kokkos_ENABLE_HIP`, `Kokkos_ARCH_AMD_GFX942_APU`,
`CMAKE_CXX_COMPILER=hipcc`, `FFT_KOKKOS=HIPFFT`, and the Cray MPICH link line.
`Kokkos_ENABLE_OPENMP` must stay **OFF** (incompatible with hipcc's second pass).

The `in.lj` Lennard-Jones melt benchmark needs **no extra packages** — `-DPKG_KOKKOS=ON
-DBUILD_MPI=ON` is the whole configure. Do not add MOLECULE/KSPACE for it.

Deviation from the usual `export CC=$(which mpicc) CXX=$(which mpic++)` rule: the preset
FORCEs `CMAKE_CXX_COMPILER=hipcc` because Kokkos-HIP requires it, and handles MPI through
explicit `-I$MPICH_DIR/include` + link flags instead of the wrapper.

Build cost is real: ~514 objects, and the `fix_*_kokkos.cpp` / `pair_*_kokkos.cpp` files
each take minutes under hipcc's two-pass GPU codegen. On a shared login node this can
crawl at ~1 object per 5 minutes. **Finish the build on a compute node** inside your
allocation (`flux run -N1 -n1 -c 96 bash -c "cd <build> && make -j 96"`) — it is roughly
an order of magnitude faster and costs nothing extra if you need the allocation anyway.

##### BLOCKER: Cray GTL vs ROCm soname mismatch

`cray-mpich/9.0.1`'s GPU-transport library needs `libamdhip64.so.6`, but ROCm 7.x ships
`.so.7`. The binary then **fails to start**: `error while loading shared libraries:
libamdhip64.so.6`. This hits the pristine build too — it is not caused by annotation.

Check which GTL matches your ROCm before choosing an MPI:

```bash
for v in /opt/cray/pe/mpich/*/gtl/lib/libmpi_gtl_hsa.so; do
  echo "$v -> $(objdump -p $v | grep -o 'libamdhip64.so.[0-9]')"
done
```

On this stack `cray-mpich/9.1.0`'s GTL needs `.so.7`. Keep `libmpi` from the MPI you
compiled against and take **only the GTL** from the matching version:

```
-L<mpich-9.0.1>/ofi/crayclang/20.0/lib -lmpi
-L/opt/cray/pe/mpich/9.1.0/gtl/lib -lmpi_gtl_hsa -Wl,-rpath,/opt/cray/pe/mpich/9.1.0/gtl/lib
```

Do NOT "solve" this by dropping `-lmpi_gtl_hsa`. Without GPU-aware MPI the run dies with
`cxil_map: write error` from the Slingshot CXI provider, because on an MI300A APU with
XNACK every buffer is device-accessible. `-pk kokkos ... comm host` does **not** avoid it.

##### Required runtime env

- `HSA_XNACK=1` — `Kokkos_ARCH_AMD_GFX942_APU` needs it for host allocations from device;
  without it Kokkos warns on every rank.
- `MPICH_GPU_SUPPORT_ENABLED=1`.

##### Launch flags

`-k on g <N>` must match the GPUs the launcher actually gave the rank. Under
`flux run -g1` (one GPU per rank) use **`-k on g 1`**; `-k on g 4` aborts every rank with
`Requested GPU with id '3' but only 1GPU(s) available!`.

Working 2-node shape: `flux run -N2 -n8 -g1 -c22` (4 ranks/node, 22 cores each, leaving
cores for the `dftracer_service` daemon on a 96-core / 4-socket node).

#### dftracer annotation

##### `main.cpp`: the `finalize()` symbol collision (silent trace loss)

`dftracer/dftracer.h` declares a **global `void finalize();`** and defines
`DFTRACER_CPP_FINI()` as `finalize()`. LAMMPS `src/main.cpp` has its own file-local
`static void finalize()` helper. Two consequences:

1. Build error: `static declaration of 'finalize' follows non-static declaration`.
2. Worse, if you resolve it the wrong way, `DFTRACER_CPP_FINI()` binds to **LAMMPS's**
   static helper — the tracer never finalizes, never flushes, and every trace is 0 bytes
   with `rc=0`.

Fix: rename the LAMMPS-local helper (e.g. `lmp_local_finalize`) at its definition and all
7 call sites. Do not rename `lammps_kokkos_finalize` / `lammps_python_finalize` /
`lammps_plugin_finalize`.

##### `main.cpp` has 7 exit paths

`main()` has six `catch` blocks (each ending in `MPI_Abort`/`MPI_Finalize`+`exit(1)`) plus
the normal fall-through. Put `DFTRACER_CPP_REGION_END` + `DFTRACER_CPP_FINI` before the
`finalize()` call on **every** one, with `DFTRACER_CPP_INIT` immediately after `MPI_Init`.
Hand-place these; the annotator's entry-point pass is unreliable on this shape.

##### Scoping a 676-file tree

`src/` has ~366 top-level `.cpp` and `src/KOKKOS/` ~310. Annotating everything is wasteful
and slow. A scope of **50 files** (37 core + 13 KOKKOS) covers the whole `in.lj -sf kk`
execution path: `main/lammps/input/run/finish/update/output/thermo/timer`,
`domain/atom/atom_vec*/comm*/irregular`, `neighbor/neigh_list/nbin*/npair`,
`integrate/verlet/modify/fix/fix_nve`, `force/pair/pair_lj_cut`, the `read_*`/`write_*`/
`dump*` I/O path, and the `*_kokkos.cpp` counterparts. Leave `lib/kokkos/` entirely alone —
brahma's GOTCHA interception captures the MPI/POSIX/STDIO layers for free, and rocprofiler
captures the GPU layer.

##### Three annotator defects seen on this tree

1. **Device code.** The clang annotator inserts `DFTRACER_CPP_FUNCTION()` into
   `KOKKOS_INLINE_FUNCTION` / `KOKKOS_FUNCTION` bodies (seen in `fix_nve_kokkos.cpp`,
   `domain_kokkos.cpp`, `nbin_kokkos.cpp`, `npair_kokkos.cpp`). Host tracing macros in
   device code do not compile and would fire per-atom. Strip any macro whose enclosing
   signature carries a `KOKKOS_*_FUNCTION` marker, and re-check after every annotate call.
2. **Include placement.** The include goes after the *last* `#include` in the file.
   `neighbor.cpp` has mid-file `#include "style_nbin.h"` blocks inside namespace scope, so
   the include landed at line 796 while macros started at line 115 — ~20 compile errors.
   Verify on **every** file that the include line number is below the first macro line;
   the safe repair is to move it directly after the *first* `#include`.
3. **The cost filter drops the hot dispatchers.** `CommKokkos::forward_comm` /
   `reverse_comm`, `NeighborKokkos::build`, `ModifyKokkos::initial_integrate` /
   `final_integrate` all score "trivial" because each body is a one-line dispatch — yet
   they are exactly what `VerletKokkos::run` calls every timestep. Add them back
   explicitly. Always read the *skipped* list, not just the annotated count.

##### Hot-loop exclusions (mandatory)

Never annotate these — they are per-atom or per-lattice-point:

- `domain.cpp`: `closest_image`, `remap`, `remap_near`, `unmap`, `minimum_image*`
- `lattice.cpp`: `lattice2box`  ← see below
- `create_atoms.cpp`: `create_atom`

`lattice2box` and `create_atom` are one-time **setup** functions but still produced
**2,721,792** and **1,024,000** events respectively — 89% of all app events in a 1M-atom
run — because they run once per lattice point / per atom. They do not inflate `Loop time`
(setup is outside it) but they dominate trace volume and bury the timestep signal.
Exclude them via `clang_annotate_file(exclude_functions=[...])`.

#### Run sizing

`bench/in.lj` scales with `-var x/y/z` (atoms = `4 * (20x)(20y)(20z)`). Measured on 2 nodes
× 4 MI300A GPUs (8 ranks): 1,024,000 atoms × 1000 steps = **4.2 s** loop time,
241.8 Matom-step/s untraced-equivalent. Scale steps, not just atoms, to reach a target
wall time. `run` is hardcoded in `in.lj` — copy the input and edit it rather than trying
to override `run` with `-var`.

#### Verified full-feature trace (2 nodes, 8 ranks, 1M atoms, 1000 steps)

~5.53M events across 8 rank traces + 2 node-service traces. All layers present:

| layer | cat | events |
|---|---|---|
| app annotation | `CPP_APP` | 4,186,332 |
| GPU runtime | `HIP_RUNTIME_API` | 719,842 |
| GPU kernels | `KERNEL_DISPATCH` | 159,965 |
| GPU copies | `MEMORY_COPY` | 64,864 |
| GPU scratch | `SCRATCH_MEMORY` | 8 |
| MPI point-to-point | `p2p` | 295,632 |
| MPI collective | `collective` | 1,504 |
| STDIO | `STDIO` | 84,284 |
| POSIX | `POSIX` | 6,176 |
| node counters | `sys`/`net`/`io` | 6,596 / 204 / 1,156 |
| PAPI | `papi` (type 11) | 62 |
| Variorum power | `gpu` (type 13) | 34 |

PAPI `PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS` all landed with
**`multiplex: 0`** — 4 counters fit the 5 hardware slots exactly. Read `multiplex` from
the compute-node trace, never from a login-node probe.

Tracing overhead at maximum feature capture: loop time 4.23 s traced vs 0.94 s with
`DFTRACER_ENABLE=0` (~4.5×), driven mostly by `HIP_RUNTIME_API` interception plus
per-timestep app events. Final thermo is **bit-identical** between the two, confirming the
annotation is correctness-preserving.

#### Cross-references

[[system_tuolumne]], [[software_rocm]], [[software_papi]], [[tools_dftracer]],
[[dftracer-annotate-cpp]], [[flux-alloc]]

## Constraints
- Do not drop -lmpi_gtl_hsa to get the binary to start.
- Leave lib/kokkos/ un-annotated; hand-place INIT/FINI in main.cpp.
- Rename only LAMMPS' file-local finalize(); not lammps_kokkos_finalize / lammps_python_finalize / lammps_plugin_finalize.
- `workload_lammps_kokkos_recipe` / `_check` render and check text only.

## Corner cases
- `error while loading shared libraries: libamdhip64.so.6` (pristine too) -> cray-mpich/9.0.1 GTL vs ROCm 7.x .so.7 -> GTL from mpich 9.1.0.
- `cxil_map: write error` -> GPU-aware MPI missing on an XNACK APU; `-pk kokkos ... comm host` does not avoid it.
- `Requested GPU with id '3' but only 1GPU(s) available!` -> -k on g 4 under flux run -g1 -> -k on g 1.
- `static declaration of 'finalize' follows non-static declaration` -> dftracer.h declares global finalize() used by DFTRACER_CPP_FINI(); resolving it wrong binds FINI to LAMMPS' helper: 0-byte traces, rc=0.
- Annotator inserts DFTRACER_CPP_FUNCTION() into KOKKOS_INLINE_FUNCTION / KOKKOS_FUNCTION bodies (fix_nve_kokkos, domain_kokkos, nbin_kokkos, npair_kokkos) -> strip; re-check after every annotate call.
- Include after the last #include: neighbor.cpp mid-file style_nbin.h includes put it at line 796 vs macros from 115 (~20 errors) -> move after the first #include.
- Cost filter drops the hot dispatchers (CommKokkos::forward_comm/reverse_comm, NeighborKokkos::build, ModifyKokkos::initial_integrate/final_integrate) -> add back; read the skipped list.
- Build on a shared login node crawls (~1 object per 5 min) -> build on a compute node inside the allocation.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_lammps_kokkos_check`, repair the proposed commands (or the recipe input), then call `workload_lammps_kokkos_recipe` and `workload_lammps_kokkos_check` again:
- `no_kokkos_openmp`: set Kokkos_ENABLE_OPENMP=OFF.
- `elcapitan_preset`: configure with -C cmake/presets/elcapitan_kokkos.cmake.
- `no_extra_packages`: drop -DPKG_MOLECULE/KSPACE.
- `gtl_kept`: add -L<mpich 9.1.0>/gtl/lib -lmpi_gtl_hsa -Wl,-rpath,....
- `gtl_soname`: take the GTL from mpich 9.1.0 (check with the objdump probe).
- `xnack`: export HSA_XNACK=1.
- `gpu_support`: export MPICH_GPU_SUPPORT_ENABLED=1.
- `gpus_per_rank`: use -k on g 1 with flux run -g1.
- `hot_exclusions`: add closest_image, remap, remap_near, unmap, minimum_image*, lattice2box, create_atom to exclude_functions.
- `no_lib_kokkos`: drop annotate calls on lib/kokkos.
- `input` (inconclusive): pass the proposed command list.
Attempts follow measured progress; the same failure twice stops the loop for the user.

## Self-heal
On a failed build or run, match the error to Corner cases and LESSONS.md (`lesson_search` the error text first), apply the fix
through the recipe, rerun. If the recipe or a rule here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: a new procedure for this workload verified by hand is added to this capability
(`capability_update`), new software or a new system met on the way becomes its own `software_<x>` / `system_<x>`; each new
error -> cause -> fix goes to LESSONS.md, each verified recipe to WORKED.md and What works.

## What works
- elcapitan_kokkos preset + -DPKG_KOKKOS=ON -DBUILD_MPI=ON, libmpi from mpich 9.0.1 and GTL from 9.1.0, built on a compute node (`make -j 96`).
- 2 nodes, 8 ranks (`flux run -N2 -n8 -g1 -c22`, `-k on g 1`), 1,024,000 atoms x 1000 steps: 4.2 s loop; full-feature trace ~5.53M events (CPP_APP 4,186,332, HIP_RUNTIME_API 719,842, KERNEL_DISPATCH 159,965, ...); traced 4.23 s vs 0.94 s DFTRACER_ENABLE=0; final thermo bit-identical.
