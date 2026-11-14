# Lessons: workload_minivite

- [L-d2332125] miniVite trace has ~2 app spans per rank -> clang_annotate_project only finds main.cpp; the solver is in dspl.hpp/graph.hpp/utils.hpp -> clang_annotate_file(language=cpp, is_entry=False) on each header (date not recorded in source; converted 2026-11-13)
- [L-4d5d0837] miniVite header parse loses functions silently -> dspl.hpp/utils.hpp use MPI types without including mpi.h -> compile_flags -include mpi.h (date not recorded in source; converted 2026-11-13)
- [L-4d4e73d2] miniVite trace gigabytes of noise -> per-vertex helpers called O(nv x iters) from every OpenMP thread -> exclude distExecuteLouvainIteration, distGetMaxIndex, distBuildLocalMapCounter (date not recorded in source; converted 2026-11-13)
- [L-4191a7cf] miniVite link fails on dftracer -> library is -ldftracer_core and the link rule uses OPTFLAGS -> put -L.../lib64 -ldftracer_core -Wl,-rpath in OPTFLAGS (override CXXFLAGS too) (date not recorded in source; converted 2026-11-13)
- [L-1646a98d] miniVite aborts at MPI_Init_thread on Cray -> MPI_THREAD_MULTIPLE check fails when OMP threads > 1 -> MPICH_MAX_THREAD_SAFETY=multiple or -DDISABLE_THREAD_MULTIPLE_CHECK (date not recorded in source; converted 2026-11-13)
- [L-789751fa] miniVite -n 4194304 at 16 ranks > 10 min -> RGG generation is O((nv/p)^2), 63.1 of 73 s at -n 2097152 -> use -f input or more ranks to study Louvain (date not recorded in source; converted 2026-11-13)
