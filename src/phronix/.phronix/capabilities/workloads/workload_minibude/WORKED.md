# What worked: workload_minibude

## minibude/hip/build
`cmake -DCMAKE_BUILD_TYPE=Release -DMODEL=hip -DCMAKE_CXX_COMPILER=<rocm>/bin/hipcc -DCXX_EXTRA_FLAGS=--offload-arch=gfx942`;
on MI300A: valid: true, max_diff_% 0.008, ~3780 GFLOP/s at -p 8 -w 64.

## minibude/hip/annotated-build
Single-token flags: `-DCMAKE_CXX_FLAGS=-I<dftracer>/include -DCXX_EXTRA_LIBRARIES=<dftracer>/lib64/libdftracer_core.so
-DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,<dftracer>/lib64 -DCXX_EXTRA_FLAGS=--offload-arch=gfx942 -DCMAKE_BUILD_TYPE=Release`;
session_build_annotated with build_subdir="source"; run from build_ann/.

## minibude/hip/annotate
Hoist `run<USE_PPWI>(...)` out of main's return before REGION_END/FINI; hand RAII guards on IMPL_CLS::fasten and
enumerateDevices in fasten.hpp; hand-annotate readNStruct<T> (comp=io, path) and run<Ns...> -> 14 CPP_APP spans/rank.

## minibude/hip/trace
2 nodes x 1 process, `--deck <annotated>/data/bm1 -i 5000 -p 8 -w 64 -o <lustre dataset>/out`, dftracer with HIP + PAPI +
variorum + hwloc: 122 362 app + 39 010 service events; no MPI/HDF5 (expected).

## tool:workload_minibude_recipe
Renders the above as JSON; `workload_minibude_check` rules on a proposed command list.
