# Lessons: software_ygm

- [L-de7872b9] DFTRACER_CPP_* macros undefined in YGM .ipp/detail headers -> dftracer.h included after <ygm/comm.hpp>; multiple test entry points -> include <dftracer/dftracer.h> after #pragma once in each annotated header (undated)
- [L-e61d3874] clang_extract_functions/clang_annotate_file return 0 functions for comm.ipp -> out-of-line methods of a class declared in a sibling .hpp; no -I for <ygm/...> -> annotate manually with Rule 0 / comp= criteria; verify with compiler + clang_lint_annotations (2026-08-04)
- [L-2d0da01f] annotated YGM does not link dftracer -> YGM CMakeLists has no dftracer knowledge; prerelease wheel's dftracer-config.cmake broken -> manual IMPORTED target linked into ygm via -DDFTRACER_ROOT (undated)
- [L-cbca9192] spdlog/fmt consteval error under Cray-clang 20.1.6 -> FetchContent'd spdlog bundled fmt incompatible with Cray-clang 20 -> PrgEnv-gnu + gcc-native/11.2 + GNU cray-mpich wrappers; rm -rf build_ann before switching (undated)
- [L-f7f43963] prerelease dftracer wheel gives no MPI-IO interception -> ldd libdftracer_core.so shows zero MPI libs -> build from source with DFTRACER_ENABLE_MPI=ON, DFTRACER_MPI_IMPL=CRAYMPICH, BRAHMA_MPI_VERSION=900001 (undated)
- [L-fa489b54] two MPI runtimes (libmpi_cray + libmpi_gnu_112) in one process -> dftracer built with Cray-clang MPI, app with PrgEnv-gnu -> build dftracer with the app's MPI wrapper; verify ldd | grep mpi (undated)
- [L-65894c0e] session_build_annotated silently ignored build_subdir for cmake -> wiring bug: only custom_build_cmd honored it -> fixed in session_tools.py; pass build_subdir="source" for nested annotated/source layout (undated)
