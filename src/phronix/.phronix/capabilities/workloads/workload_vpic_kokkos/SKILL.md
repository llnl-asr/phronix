---
name: workload_vpic_kokkos
description: VPIC-Kokkos (TauferLab/vpic-kokkos devel + write_functions, lanl/vpic-kokkos) - Release build with Cray wrappers, parallel HDF5, the two-stage deck-compile pattern and annotated-install symlinks, annotation quirks (bare-identifier REGION macros, misleading comp labels), deck sizing (Weibel smoke, sized short_pulse, production portability_test decks, benchmark.cxx ENABLE_OUTPUT), run command with --tpp and the static TLS tunable, the measured MPI-communication-bound diagnosis and the energy-reduction patches (field_advance_kernels_t segfault). Load for vpic, vpic-kokkos, "Bad domain decompostion", "expected ';' after expression" on DFTRACER_CPP_REGION_START, libsci_cray_mp.so TLS error.
---
Cross-references: [[software_flux]], [[tools_session_deps]], [[tools_parallel]], [[workload_ipic3d]], [[ropt_campaign]], [[software_mpi]], [[software_hdf5]], [[system_tuolumne]], [[tools_dftracer]]

# workload_vpic_kokkos

VPIC-Kokkos (TauferLab/vpic-kokkos, branch devel; write_functions adds HDF5 and excludes ghost cells; also github.com/lanl/vpic-kokkos).
Public repo: clone over HTTPS (`GIT_TERMINAL_PROMPT=0`) when no SSH key is on GitHub. Version 3 merges dftracer-agents'
`workload-vpic-kokkos` skill (cross-references there: dftracer-annotation-lessons, dftracer-diagnoser, software-mpi,
bug-dftracer-crayclang-python-abi). Tools: `vpic_cmake_args`, `vpic_run_command`, `vpic_deck_prepare` and
`workload_vpic_kokkos_recipe` predict; `vpic_build_check` and `workload_vpic_kokkos_check` validate.

## Rules
- Configure with `vpic_cmake_args`: Cray `cc`/`CC` wrappers, Kokkos OpenMP, `CMAKE_BUILD_TYPE=Release`. `session_configure` forces RelWithDebInfo and VPIC's deck wrapper adds `-O3` only for Release, so decks run ~25x slower; discard such baselines.
- VPIC is CPU-only by default on this codebase (Kokkos Serial+OpenMP backend, bundled Kokkos submodule): do not assume HIP/CUDA offload just because the target has GPUs; check the app's own CMake defaults first. CMake flags: `-DBUILD_INTERNAL_KOKKOS=ON -DENABLE_KOKKOS_OPENMP=ON -DENABLE_KOKKOS_CUDA=OFF`.
- write_functions (HDF5): build parallel HDF5 1.14 from source with the dftracer session tools, pass `hdf5_root` to `vpic_cmake_args` (adds `HDF5_ROOT` and `HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON`), annotate with compile flag `-DVPIC_ENABLE_HDF5`, and give `vpic_run_command` the `hdf5_lib_dir`.
- Two-stage build: CMake produces a `vpic` compiler-wrapper script, NOT a runnable simulation binary. Each input deck (`.cxx`) is compiled into its own executable by running `<build>/bin/vpic path/to/deck.cxx`, which internally invokes the real MPI C++ compiler with the deck + `deck/main.cc` + `deck/wrapper.cc` and links against `libvpic.a`. `install/bin/vpic` is broken in the devel tree (paths to missing install/deck, install/src): use `<build>/bin/vpic`.
- When building an ANNOTATED copy under a different install prefix (`install_ann/` vs `install/`), the generated `vpic` wrapper script may be missing pieces the original didn't need to regenerate: check for/symlink `install_ann/deck` -> the annotated `deck/` sources (`main.cc`/`wrapper.h` are installed to `share/vpic/`, not always to a `deck/` subdir), symlink `install_ann/src` -> the annotated source's `src/` (header search path used by the deck-compile step), and symlink `install_ann/libvpic.a` at the install root if the generated script's `-L` list doesn't include `lib/`. The dftracer link flags (`-I<dftracer include> -L<dftracer lib> -Wl,-rpath,<dftracer lib> -ldftracer_core`) must be added explicitly to the generated `vpic` wrapper script too: VPIC's own CMake has no dftracer awareness.
- VPIC's real I/O layer is `src/util/checkpt/checkpt_io.cc` (thin wrapper over `CheckPtIO`), not `FileIO.h` (a header-only template, correctly skipped by the annotation cost filter). Main simulation loop is `vpic_simulation::advance()` in `src/vpic/advance.cc`, called from `deck/main.cc`'s `while (simulation->advance())`.
- Run with `vpic_run_command`: threads via `--tpp N` (not OMP_NUM_THREADS), `GLIBC_TUNABLES=glibc.rtld.optional_static_tls=1000000` (libsci_cray_mp.so), Cray PE dirs on LD_LIBRARY_PATH, absolute deck path.
- Size the deck with `vpic_deck_prepare`: short_pulse 640x640, nppc 100, 80 steps, dumps every 20, restart 40, particle block enabled, topology 2x1x2 = 4 ranks: ~5 GB in ~12 s on 1 node.
- Smoke deck: `sample/Weibel/Weibel.cxx` is a genuinely small deck: `nppc=200`, `nx=64, ny=nz=1` -> only 12,800 total macro particles, `num_step=1000`, and `topology_x = nproc()` auto-adapts to whatever rank count you launch with (no fixed decomposition requirement). Right deck for a smoke test / quick best-case trace: well under a minute at 4-16 ranks on a single node.
- Annotate (clang_annotate_file language=cpp, is_entry on deck/main.cc) src/vpic/dump.cc, vpic.cc, src/util/checkpt/checkpt.cc; exclude hot kernels.
  - `DFTRACER_CPP_FUNCTION()` is RAII-scoped: there is no C++ END macro; only `DFTRACER_CPP_FUNCTION()` + `DFTRACER_CPP_FUNCTION_UPDATE("comp", ...)` at the top of every non-`main` function.
  - `main()` uses `DFTRACER_CPP_INIT` + `DFTRACER_CPP_REGION_START(main)` at entry and `DFTRACER_CPP_REGION_END(main)` + `DFTRACER_CPP_FINI()` before the single `return`.
  - **`DFTRACER_CPP_REGION_START`/`END` take a BARE IDENTIFIER, not a string literal.** The macro expands via `##name` token-pasting (`DFTracer* profiler_##name = ...` / `delete profiler_##name`), so `DFTRACER_CPP_REGION_START("main")` fails to compile (`expected ';' after expression`): it must be `DFTRACER_CPP_REGION_START(main)`.
  - **A `comp=` label based on a function's NAME is not reliable evidence of what it does.** `dump_energies` was annotated `comp="io"` but is actually 99.7% `MPI_Allreduce` by wall time: a communication routine (general rule in dftracer-diagnoser pitfalls).
- Before concluding "this workload has no I/O," grep any deck for an `ENABLE_OUTPUT`-style compile-time gate (see Corner cases: benchmark.cxx).
- Campaign (demo): scope carries env_extra (TLS tunable, LD_LIBRARY_PATH incl. HDF5 lib, OMP binding), run_command `./<deck>.Linux --tpp 24`, ppn 4; test_command compiles the smoke and write decks with bin/vpic then runs the 1-rank smoke deck. Match: per-process classes -> rabbit-xfs, the shared HDF5 class -> rabbit-gfs2 when Rabbit Lustre cannot be allocated (approx gate); ropt_optimize_finalize needs custom_build_cmd that rebuilds the lib and the decks. Result seen: app 23 s -> 15 s, I/O 5.9x.
- Use ropt_compare_* / ropt_analyze_* and session_deps for outputs and dependencies, not ad-hoc ls/zcat probes ([[tools_session_deps]]).

### Measured diagnosis (Tuolumne, 16 ranks/1 node, Weibel deck, best_case trace)
VPIC is **MPI-communication-bound**, not I/O-bound: 82% of the per-timestep `advance()` loop's wall time is `MPI_Allreduce` (the
`dump_energies` global energy-diagnostic reduction, 1.65 s/3008 calls) unioned with `boundary_p_kokkos` (particle/halo boundary
exchange, MPI_Wait-dominated). Pure Kokkos compute inside `advance()` (excluding both) is only ~18% of the loop. POSIX/STDIO I/O is
negligible (<0.2% of total time; no real file reads/writes in this configuration, just `access`/`fopen`-class metadata calls).
Optimization should target reducing/overlapping the `MPI_Allreduce` cost (e.g. non-blocking `MPI_Iallreduce`, less frequent
energy-diagnostic cadence traded against physics-validity, or reduced message/wait imbalance in the boundary exchange): not I/O
tuning, and not "do less work" moves that reduce the diagnostic's frequency without justifying it against the physics
requirement (feedback-app-pattern-swap-not-optimization).

### Optimization candidates (STEP 8 findings)
Root cause of the `MPI_Allreduce` cost: `dump_energies` (`src/vpic/dump.cc:41`) issues THREE separate small blocking `mp_allsum_d`
reductions per timestep: one 6-double field-energy reduction (`energy_f_kokkos`, `src/field_advance/standard/energy_f.cc:207`) and
one 1-double-per-species reduction (`energy_p_kokkos`, `src/species_advance/standard/energy_p.cc:208`). Three separate small-message
blocking collectives per step is sync-bound (latency-dominated, not bandwidth-dominated).
- **PATCH #1 (primary, highest confidence):** coalesce all three into ONE `MPI_Allreduce` over a packed `[6 + Nspecies]`-double
  buffer. Physics-identical (linear MPI_SUM is associative over the concatenated buffer): a pure message-aggregation fix, cite
  Thakur & Gropp, IJHPCA 2005. Both `energy_f_kokkos`/`energy_p_kokkos` are library code (`libvpic.a`), not deck code: applying
  this requires an incremental relink of the app library (Kokkos objects are unaffected, so a relink is ~2-5 min, not a full
  rebuild), not just recompiling a deck.
- **PATCH #1, species subset: IMPLEMENTED AND VERIFIED (2026-07-14)** (see What works).
- **PATCH #1's field-energy half: ATTEMPTED AND REVERTED (2026-07-14)** (see Constraints and Corner cases).
- **PATCH #2 (stacks on #1):** switch to non-blocking `MPI_Iallreduce` for the coalesced energy reduction, since the result is only
  consumed by rank-0's diagnostic printout: it is off the critical path and can overlap with the next timestep's compute. Cite
  Hoefler et al., SC 2007. Unaffected by the struct finding (no struct change needed): the next thing to try, but only after
  finding a way to expose a local-only field-energy variant WITHOUT growing `field_advance_kernels_t` (e.g. a free function outside
  the kernel vtable, dispatched via the existing single-material `if` check duplicated at the call site in `dump.cc` instead of via
  a new struct member).
- **Secondary, cheap, no-rebuild:** VPIC's own run scripts never set `OMP_NUM_THREADS`/`OMP_PROC_BIND`/`OMP_PLACES` even though
  the build is Kokkos-OpenMP: verify actual thread count/affinity at runtime before assuming all cores are used; a pure
  environment-variable check, test it alongside any PATCH #1/#2 validation since it's nearly free.
- **Explicitly NOT worth pursuing:** pinned-memory/cross-NUMA placement (MI300A's unified CPU+GPU HBM domain makes these
  structurally inert), launcher-level CPU affinity (`flux cpu-affinity` confirmed to have no measurable effect on this system,
  twice, across different workloads: tune via `OMP_PLACES` inside the process instead), and I/O/ROMIO/Lustre-striping tuning
  (measured, see Corner cases: benchmark.cxx).

## Constraints
- Annotated tree needs dftracer in the root CMakeLists (find_package, libdftracer_core + rpath in VPIC_CXX_LIBRARIES used by the deck wrapper, `dftracer::dftracer_core` on target vpic); pass `-Ddftracer_DIR` and `-DCMAKE_CXX_FLAGS=-I<dftracer include>` (no spaces in a token).
- Output goes to the PFS (/p/vast1 here), not Rabbit, until redirected.
- The demo optimizer pass (ropt_match_optimizer) skips demo campaigns; code-level HDF5 tuning (chunking, compression, subfiling) changes layout and needs user approval.
- **DO NOT grow `field_advance_kernels_t` (do not add any member to it, for any reason)** until the hardcoded layout assumption is found (see Corner cases).
- `portability_test_x<N>-y<M>-z<K>.cxx` decks are not smoke decks; they REQUIRE exactly `N*M*K` ranks.

## Corner cases
- `git@github.com Permission denied (publickey)` -> no key on GitHub -> clone via https -> `git ls-remote https://...` lists refs.
- mpicxx `crayCC not found` -> MCP env wrapper -> use the Cray `CC` -> configure passes.
- `libsci_cray_mp.so` static TLS error -> add the TLS tunable -> run exits 0.
- CMake finds HDF5 via config file with the wrong target -> `HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON` with HDF5_ROOT -> configure passes.
- clang_annotate_file mangles an if/else with macro bodies in checkpt.cc (~line 476) -> fix braces with session_edit_file -> annotated build compiles.
- The annotator rewrites CRLF files (write.cc) with LF -> whole-file diff; patches must be byte exact.
- ropt_alloc_create TypeError with string args -> use flux_alloc ([[software_flux]]).
- Tracing overhead: 211M fwrite calls traced; compare untraced runs for timing.
- `TestScripts/data/portability_test*.cxx` decks (including the smallest-named `portability_test_x2-y2-z2.cxx`) are FULL PRODUCTION SCALE: ~80M particles/rank, 5302 timesteps. They take far longer than a short pdebug allocation and their name only encodes the MPI domain-decomposition shape (`x2-y2-z2` = 2x2x2 = 8 ranks required), not problem size. The wrong rank count fails immediately with `Bad domain decompostion (NxMxK)` at `src/grid/partition.cc`.
- **`sample/benchmark.cxx` has I/O compiled out by default.** `sample/benchmark.cxx:18` hardcodes `#define ENABLE_OUTPUT 0`, which wraps the ENTIRE diagnostics/dump block (`dump_mkdir`, `dump_energies`, field/particle/hydro dumps: everything between the `#if ENABLE_OUTPUT` at line 1059 and its matching `#endif`) out of the binary. A trace shows 0.000 MB/s I/O bandwidth and an empty run directory (just the binary + `params.txt`): NOT a dftracer/analyzer misconfiguration, it's the deck's own intentional design (isolate compute+communication from I/O noise). To measure real I/O, flip the macro to `1` and relink the deck: an incremental compile of just `main.cc`+`wrapper.cc`+the deck against the already-built `libvpic.a`, ~1 minute.
  - **Measured I/O profile with `ENABLE_OUTPUT=1`** (128 ranks/8 nodes, `benchmark.cxx`, dumps at T.0/T.500/T.1000 -> `field/`, `particle/`, `ehydro/`, `I1hydro/`, `I2hydro/`, `restart/`, `rundata/energies`, 1.8 GB total on Lustre): 340.85M POSIX ops for only 325.0 MB transferred (196.9 MB/s aggregate), but only **1.65 s of actual I/O time out of 210.2 s job time** (<1%). Average transfer size is a small fraction of a byte per op: a pronounced small-I/O anti-pattern (dump routines write per-cell/per-particle rather than batching), but total I/O time is tiny next to communication (82% of the timestep loop), confirming and superseding the earlier "untested, no real file I/O" caveat from the Weibel-only diagnosis. **Verdict: I/O/ROMIO/Lustre-striping levers are NOT worth pursuing**; if I/O ever mattered at larger scale, the lever would be write-coalescing (batch per-cell/per-particle writes), not ROMIO/striping tuning, since the shape is op-count-bound, not bandwidth-bound.
- **Growing `field_advance_kernels_t` segfaults (2026-07-14).** Adding a new function-pointer member to this struct (even completely unused, unregistered, never called; tested with a plain `void*` pad field) causes a **reproducible segfault ~35 s into every 128-rank/8-node run**, at a different random rank/node each time (never the same rank twice across 3 reproductions), always before the first `status_interval` print, i.e. inside the very first real physics `advance()`, nowhere near the field-energy dump code. Isolated via 3 A/B tests on the same allocation: (1) full patch: crash; (2) call path reverted to the old `energy_f_kokkos()` but struct member left in place, unused: same crash; (3) struct member replaced with an unregistered `void*` pad of the same size, everything else reverted: still crashes. So the crash is caused by the struct's SIZE changing at all. Root cause not found (ruled out: the coalescing logic itself and the CHECKPT_SYM machinery: `checkpt_field_advance_kernels`/`restore_field_advance_kernels` only run when checkpointing triggers, which this deck never does since `restart_interval=0`). Suspect: something elsewhere, possibly the MPI boundary-exchange (`boundary_p.cc`) buffer serialization, since `field_array_t` embeds `field_advance_kernels_t kernel[1]` BY VALUE followed immediately by `field_buffers_t* fb` and several `Kokkos::View` members whose byte offsets shift: a hardcoded layout/offset somewhere that a header-only, fully-rebuilt change doesn't fix. Reverted via `git checkout` on all 6 touched files (`field_advance.h`/`.cc`, `sfa.cc`, `sfa_private.h`, `energy_f.cc`, `vacuum_energy_f.cc`), keeping only the species-only half. `energy_f_kokkos` is a `CHECKPT_SYM`/`RESTORE_SYM`-registered function pointer with a second runtime-selected variant (`vacuum_energy_f_kokkos`), so coalescing it needs to touch `field_advance.h`/`.cc`, `sfa.cc`, `sfa_private.h` too.

## Corrector
- Run `vpic_build_check` after any configure; apply its fix and rebuild.
- `workload_vpic_kokkos_check`: `release_build` / `kokkos_openmp` / `no_mpicxx_compiler` -> regenerate the configure line with `vpic_cmake_args`; `region_bare_identifier` -> `DFTRACER_CPP_REGION_START(main)`; `no_grow_field_kernels` -> revert the struct change, use a free function dispatched in dump.cc; `tpp_threads` / `static_tls` -> regenerate the run line with `vpic_run_command`; `no_flux_cpu_affinity` -> drop it, use OMP_PLACES; `deck_decomposition` -> match ranks to N*M*K or use the Weibel deck; `input` (inconclusive) -> pass the commands. Then predict and validate again; the same failure twice stops the loop.

## Self-heal
On a failed build or run, match the error to Corner cases, apply the fix through the tools above, rerun; locate deps with [[tools_session_deps]].

## Self-learn
What is explored here becomes a capability: when a new VPIC procedure is verified by hand, call exploration_complete so it is added to this capability (capability_update); propose a lesson (lesson_propose) for each new error -> cause -> fix -> verify; one-offs go to LESSONS.md.

## Parallel plan
Plan with [[tools_parallel]]: clone devel and write_functions, module probes and session_deps in one message; build and annotate in parallel branches; traced and untraced runs are sequential (same nodes).

## What works
- Weibel smoke deck at 4-16 ranks on one node: well under a minute; best-case trace gives the MPI-bound diagnosis above.
- Sized short_pulse via `vpic_deck_prepare` (4 ranks x 24 threads, --tpp 24, TLS tunable): ~5 GB in ~12 s on 1 node.
- Campaign demo with Rabbit: app 23 s -> 15 s, I/O 5.9x.
- **PATCH #1 species subset (2026-07-14):** added `energy_p_local()` (`src/species_advance/standard/energy_p.cc`, declared in `species_advance.h`): `energy_p_kokkos()` minus its internal `mp_allsum_d`; `dump_energies()` calls it per species, accumulates into one buffer, and issues ONE `mp_allsum_d` for all species. Rebuild: `make vpic` in `build_ann/` (12 s, ~8 files recompile) + a deck relink (~10 s). Verified via full-file `diff` of `rundata/energies` between pre- and post-patch 128-rank runs: **byte-identical output at every timestep** (cvac^2 scaling commutes with summation across species): physics-preserving. Wall-time delta on a 2-species (`I2`, `electron`) benchmark.cxx deck: none measurable (124.29 s vs 124.03 s): removing 1 extra blocking call out of ~1000 timesteps is below the noise floor at this species count; expect a real win only for decks with many species or much higher `energies_interval` frequency.
- benchmark.cxx with `ENABLE_OUTPUT=1` relinked in ~1 min: real dumps (1.8 GB) measured at 128 ranks/8 nodes.
