# Lessons: workload_smith

- [L-0b5a551f] Smith host-config TPLs 'Permission denied' -> host-configs point at a restricted-group shared workspace (drwxrws---) -> read pins only, rebuild the TPLs in the session (date not recorded in source; converted 2026-11-13)
- [L-b8a31cdc] Smith build dies 'no member named format in namespace std' -> ~33 sources use std::format without #include <format> and libstdc++ 13 does not pull it in -> add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-include$<SEMICOLON>format>) in src/ and examples/ CMakeLists (date not recorded in source; converted 2026-11-13)
- [L-b791aa37] Smith std::format unavailable with clang on TOSS4 -> system libstdc++ too old -> --gcc-toolchain=/opt/rh/gcc-toolset-13/root/usr + gcc 13 rpath (date not recorded in source; converted 2026-11-13)
- [L-497586c4] smith_numerics fails to compile without SuperLU -> SuperLUSolver declared outside #ifdef MFEM_USE_SUPERLU -> build SuperLU_DIST; adding SUPERLUDIST_DIR to an existing build dir does nothing (cache set): fresh build dir (date not recorded in source; converted 2026-11-13)
- [L-542a8e6f] All Smith examples fail to compile on StrumpackSolver -> unguarded use in solid_mechanics_contact.hpp -> guard with #ifdef MFEM_USE_STRUMPACK else SuperLUSolver (or build STRUMPACK ~1 h) (date not recorded in source; converted 2026-11-13)
- [L-a84772b3] Smith driver target does not build -> commented out upstream, smith.cpp stale (12 no matching constructor errors) -> run an example (composable_thermo_mechanics) (date not recorded in source; converted 2026-11-13)
- [L-87ecaa49] Smith traces all 0 bytes with rc=0 -> annotation scoped to src/ only, no INIT/FINI -> annotate the example main after ApplicationManager (date not recorded in source; converted 2026-11-13)
- [L-a87bdfaa] Smith traced run 2.5x slower -> GetElementVDofs per-element accessor ~61% of app events -> exclude_functions=[GetElementVDofs] for low-overhead traces (date not recorded in source; converted 2026-11-13)
