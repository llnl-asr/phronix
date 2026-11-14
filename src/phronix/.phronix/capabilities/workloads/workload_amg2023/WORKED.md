# What worked: workload_amg2023

## amg2023/build/hypre
git clone --depth 1 --branch v2.32.0 hypre; ./configure --prefix=<ws>/hypre --with-MPI --with-openmp --enable-shared CC=$CC CXX=$CXX; make -j 8 && make install; HYPRE_config.h shows HYPRE_USING_OPENMP 1, SEQUENTIAL/HIP/CUDA undef.

## amg2023/build/cmake
cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DHYPRE_PREFIX=<ws>/hypre -DAMG_WITH_MPI=TRUE -DAMG_WITH_OMP=TRUE; link -ldftracer_core for the annotated build.

## amg2023/baseline/2node
2 nodes x 8 ranks, -P 4 2 2 -n 240 240 240 -problem 1: 70.8 s, rc=0, 16/16 rank + 2/2 service traces, 20,597,216 app events, C_APP 32 (2/rank) (2026-08-31).

## tool:workload_amg2023_recipe
renders the above; workload_amg2023_check flags -ldftracer, in-source cmake, missing -DHYPRE_PREFIX and a -P product != ranks.
