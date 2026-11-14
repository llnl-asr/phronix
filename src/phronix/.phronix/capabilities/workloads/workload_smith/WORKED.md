# What worked: workload_smith

## smith/build/codevelop
SMITH_ENABLE_CODEVELOP=ON; TPLs METIS 5.1.0, ParMETIS 4.0.3 (mfem/tpls mirror), hypre, serial HDF5, camp (-DBLT_SOURCE_DIR=<smith>/cmake/blt), Conduit (BLT at <conduit>/src/blt), SuperLU_DIST; --gcc-toolchain=<gcc-toolset-13>; -include format patch; STRUMPACK guard; fresh build dir.

## smith/run/composable_thermo_mechanics
MakeCartesian3D(80,20,20,...), 5 steps; 2 nodes x 16 ranks CPU MPI: 81 s pristine, 201 s traced.

## smith/annotate/cpp
compile_flags from compile_commands.json plus -I <tree>/src -isystem <tree>/gretl/src -I<dftracer include>; annotate the example main (INIT after ApplicationManager, FINI before the final return).

## tool:workload_smith_recipe
Renders the above; workload_smith_check passes a codevelop + gcc13 + SUPERLUDIST_DIR configure.
