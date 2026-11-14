# What worked: workload_amg

## amg/build/make
export CC=$(which mpicc); add the HYPRE_BoomerAMGGetCumNnzAP prototype to parcsr_ls/HYPRE_parcsr_ls.h; make -j 8 | tee build.log; grep -c 'error:' build.log == 0; ls test/amg.

## amg/instrument/link
Makefile.include: INCLUDE_CFLAGS += $(DFTRACER_CFLAGS); INCLUDE_LFLAGS = -lm -fopenmp $(DFTRACER_LDFLAGS) -ldftracer_core; ldd test/amg | grep dftracer.

## amg/instrument/annotate
clang_annotate_project with -I<ann>/source{,/utilities,/IJ_mv,/seq_mv,/parcsr_mv,/parcsr_ls,/krylov} -I<cray-mpich>/include -DHYPRE_BIGINT -DTIMER_USE_MPI -DHYPRE_USING_OPENMP -DHYPRE_HOPSCOTCH -DHYPRE_USING_PERSISTENT_COMM -DHYPRE_TIMING, the 16 utilities exclusions and exclude_functions hypre_qsort2abs, hypre_CSRMatrixGetLoadBalancedPartitionBoundary; then clang_annotate_file(source/test/amg.c, is_entry=True); move INIT/FINI around hypre_MPI_Init/Finalize by hand (388 functions annotated).

## amg/smoke/semantics
annotated binary, DFTRACER_ENABLE=0, -problem 1 -P 1 1 1 -n 20 20 20: Iterations = 17, Final Relative Residual Norm = 6.589910e-09 (exact match of pristine).

## amg/baseline/2node
flux run -N 2 -n 8 -c 20, OMP_NUM_THREADS=8, test/amg -P 2 2 2 -n 100 100 100 -problem 1: rc=0, 13 s, 1,318,447 events.

## tool:workload_amg_recipe
workload_amg_recipe(ranks=N) returns the derived -P; workload_amg_check fails a -P whose product != launcher ranks.
