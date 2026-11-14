# Lessons: workload_kripke

- [L-d20995b5] Kripke CMake fails 'The BLT submodule is not present.' / 'CAMP submodule not initialized' -> eight submodules not fetched -> git submodule update --init --recursive (date not recorded in source; converted 2026-11-13)
- [L-5a106e94] Kripke build hidden behind ExternalProject and slow -> top-level CMakeLists is a superbuild for adiak/Caliper; RAJA builds ~100 tutorial binaries -> configure cmake/kripke with KRIPKE_SOURCE_ROOT, RAJA_ENABLE_*=Off, build kripke.exe (date not recorded in source; converted 2026-11-13)
- [L-68fa9073] Kripke annotation reports functions: 0 green -> KripkeConfig.h/RAJA/camp headers not found -> pass compile_flags with build and RAJA include dirs (date not recorded in source; converted 2026-11-13)
- [L-8eda807e] Kripke trace lacks sweepSubdomain -> cost filter scores timer-macro+dispatch bodies trivial -> clang_insert_line DFTRACER_CPP_FUNCTION() + comp UPDATE for sweepSubdomain, SweepComm functions, generateEnergy (date not recorded in source; converted 2026-11-13)
- [L-c6ff89b5] Kripke FINI after MPI teardown -> MPI_Finalize wrapped in Comm::finalize(), anchor and lint L3 match the literal symbol -> move REGION_END+FINI above Comm::finalize(); add FINI in usage() (date not recorded in source; converted 2026-11-13)
