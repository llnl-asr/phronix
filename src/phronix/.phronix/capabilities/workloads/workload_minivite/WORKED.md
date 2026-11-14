# What worked: workload_minivite

## minivite/build/make
`make -j 8 CXX=$CXX CXXFLAGS="-std=c++11 -g -O3 -fopenmp -DPRINT_DIST_STATS -I<dftracer>/include" OPTFLAGS="-O3 -fopenmp -DPRINT_DIST_STATS -L<dftracer>/lib64 -ldftracer_core -Wl,-rpath,<dftracer>/lib64"`.

## minivite/annotate/cpp
main.cpp + the three headers with compile_flags `-std=c++11 -fopenmp -DPRINT_DIST_STATS -I<mpi include> -include mpi.h`, exclude the three hot helpers: 17 traced functions.

## minivite/run/2node
`-n 2097152`, 2 nodes x 8 ranks x 11 threads, MPICH_MAX_THREAD_SAFETY=multiple, PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS: 73 s, modularity 0.75311.

## tool:workload_minivite_recipe
Renders the above; workload_minivite_check passes the make line and a run with MPICH_MAX_THREAD_SAFETY=multiple.
