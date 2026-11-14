# What worked: workload_laghos

## laghos/build/make
module load rocm/6.4.2 rocmcc/6.4.2-cce-20.0.0-magic cray-mpich/9.0.1 cmake/3.29.2; dos2unix laghos.cpp; LC_ALL=C tr -cd '\0-\177'; README seds on config.mk/test.mk; set +e; make; set -e; ls *.o; README explicit link.

## laghos/instrument/install
session_install_dftracer(hdf5=False, hip=True, rocm_path=/opt/rocm-6.4.2).

## laghos/instrument/annotate
clang_annotate_project with -std=c++17 -D__HIP_PLATFORM_AMD__=1 -DUSE_PROF_API=1 -DCAMP_HAVE_HIP -DFMT_HEADER_ONLY=1 -I<prefix>/include -I<prefix>/include/mfem -I<rocm>/include -I<rocm>/include/rocrand -I<mpich>/include -I<dftracer include>; add Mult and AssembleForceMatrix by hand; FINI on all five exits of main.

## laghos/baseline/4node
4 nodes x 16 ranks, -g1 -c23, -p 1 -dim 3 -rs 3 -tf 0.15 -pa -d hip, SELECTIVE aggregation dur<100: 343 s, Energy diff 6.90e-06, rc=0, 0 truncated (2026-08-13).

## laghos/baseline/papi_exact
9 runs with DFTRACER_PAPI_EVENTS=<subset> DFTRACER_PAPI_MULTIPLEX=0, rs=3 tf=0.10: 9/9 rc=0, 30/30 counters exact; stage all runs (service traces prefixed) and dftracer_split --output <out> --chunk-size <MB> once (2026-08-13).

## tool:workload_laghos_recipe
renders the above; workload_laghos_check flags PrgEnv-cray, lowercase aggregation type, bad split flags, unverified PAPI subsets.
