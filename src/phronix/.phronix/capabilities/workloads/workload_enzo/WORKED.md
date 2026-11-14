# What worked: workload_enzo

## enzo/build/tuolumne
`./configure` at the repo root (enzo-2.6.1); self-written `Make.mach.tuolumne` (Cray mpicc/mpicxx, gcc-toolset-13 gfortran,
rpath to HDF5 1.10.11 and libgfortran, `$(DFTRACER_LIBS)` in MACH_LIBS); in `src/enzo`: `gmake machine-tuolumne opt-aggressive
use-mpi-yes grackle-no` then `gmake -j32`, after the two Cray-clang 20 source fixes (`&reference`, `"..." __FILE__`).

## enzo/annotated/build
`gmake clean`; `gmake MACH_INCLUDES="-I$HDF5_DIR/include -I<dftracer>/include"
DFTRACER_LIBS="-L<dftracer>/lib64 -Wl,-rpath,<dftracer>/lib64 -ldftracer_core" -j32`, with dftracer.h first include, FINI in
my_exit(), ActiveParticleType/StochasticForcing excluded, RadiativeTransferHealpixRoutines64.C unannotated.

## enzo/smoke
1 process, `StopCycle = 10` appended to gas_plus_dm_amr_multiphys.enzo, `enzo.exe -d gas_plus_dm_amr_multiphys.enzo` -> ~0.8 s.

## enzo/run/16-3
1 node x 32 ranks, env `DFTRACER_ENABLE=1 DFTRACER_INIT=FUNCTION DFTRACER_INC_METADATA=1 DFTRACER_DATA_DIR=all
DFTRACER_TRACE_COMPRESSION=1`: full z=99->0, 320 cycles, 560 s, 12 RD outputs; 358 M events, 3.0 GB.

## tool:workload_enzo_recipe
Renders the above as JSON; `workload_enzo_check` rules on a proposed command list.
