# What worked: workload_rajaperf

## rajaperf/build/cmake
cmake -DENABLE_HIP=ON -DENABLE_MPI=ON -DRAJA_PERFSUITE_ENABLE_MPI=ON -DENABLE_OPENMP=ON -DENABLE_TESTS=ON -DCMAKE_PREFIX_PATH='/opt/rocm-7.2.1;<dftracer prefix>' -DRAJA_ENABLE_EXTERNAL_ROCPRIM=ON -Drocprim_DIR=/opt/rocm-7.2.1/lib/cmake/rocprim (2026-08-05, Tuolumne).

## rajaperf/instrument/link
after set(RAJA_PERFSUITE_DEPENDS RAJA): find_package(rocprofiler-sdk CONFIG REQUIRED); find_package(dftracer REQUIRED); list(APPEND RAJA_PERFSUITE_DEPENDS dftracer).

## rajaperf/instrument/annotate
DFTRACER_CPP_FUNCTION() + DFTRACER_CPP_FUNCTION_UPDATE("comp", ...) in Executor::runSuite/runKernel and KernelBase::execute/runKernel; main(): DFTRACER_CPP_INIT() first, REGION_START(main)/REGION_DYN_UPDATE(main, "comp", "cpu")/REGION_END(main), FINI before return 0; lint clean; full build links.

## rajaperf/baseline/4node
flux run -N 4 -n 16 --exclusive <build>/bin/raja-perf.exe --kernels <Group_Name...> --variants Base_Seq Base_HIP --outdir <dir>; verify 16 PIDs, 4 hosts, checksum report for 16 ranks, timing CSVs.

## tool:workload_rajaperf_recipe
renders the above with the full kernel/variant lists; workload_rajaperf_check rejects unknown --kernels names and the regression flags.
