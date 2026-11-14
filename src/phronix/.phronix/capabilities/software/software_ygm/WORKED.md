# What worked: software_ygm

- [ygm/smoke/test_comm] Single-process test/test_comm.cpp on the annotated tree: 194 events, CPP_APP (post_new_irecv, check_completed_sends, local_process_incoming, barrier_reduce_counts, priv_barrier, comm_setup) + POSIX + dftracer metadata; FUNCTION mode works without MPI-IO interception. (undated)
- [ygm/build/prgenv_gnu] module load PrgEnv-gnu gcc-native/11.2; CC/CXX = cray-mpich GNU mpicc/mpicxx; rm -rf build_ann; cmake with C++20, -DYGM_BUILD_TESTS=ON, -DDFTRACER_ROOT=<dftracer prefix> (IMPORTED target). (undated)
