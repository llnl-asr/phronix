# Lessons: workload_amg2023

- [L-0288c57c] AMG2023 annotated main got FUNCTION_START but no DFTRACER_C_INIT/FINI at all -> entry-point pass did not fire, likely because the signature is split as 'hypre_int\nmain( hypre_int argc,' with a non-int return type -> insert INIT after hypre_MPI_Init and FINI before hypre_MPI_Finalize by hand (2026-08-31)
- [L-26e7c92e] AMG2023 DFTRACER_C_FUNCTION_END placed after hypre_MPI_Finalize and clang_lint_annotations passed -> lint L3 matches only the literal MPI_Finalize -> move END+FINI before hypre_MPI_Finalize on all five exits and add FINI to both BuildIJLaplacian* exit(1) checks (2026-08-31)
- [L-db71aa73] AMG2023 annotated build fails to link -> session_patch_build links -ldftracer, which does not exist -> patch target_link_libraries to -ldftracer_core (2026-08-31)
- [L-374bf950] AMG2023 Makefile build fails -> HYPRE_DIR hardcoded to someone's home dir and unconditional CUDA/Umpire links -> use the CMake build out-of-source with -DHYPRE_PREFIX (2026-08-31)
- [L-7680963a] PAPI multiplex=1 on a login-node probe but 0 on compute nodes for the same 4 presets -> multiplexing depends on the node type -> read multiplex from the trace of the run itself (2026-08-31)
