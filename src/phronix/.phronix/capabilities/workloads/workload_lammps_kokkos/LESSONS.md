# Lessons: workload_lammps_kokkos

- [L-be490fee] LAMMPS-KOKKOS binary fails to start 'error while loading shared libraries: libamdhip64.so.6' (pristine too) -> cray-mpich/9.0.1 GTL built for ROCm 6, ROCm 7.x ships .so.7 -> keep libmpi, link only -lmpi_gtl_hsa from /opt/cray/pe/mpich/9.1.0/gtl/lib with rpath (date not recorded in source; converted 2026-11-13)
- [L-7e96185b] LAMMPS run dies 'cxil_map: write error' -> -lmpi_gtl_hsa dropped, no GPU-aware MPI on an XNACK APU -> keep the matching GTL; comm host does not help (date not recorded in source; converted 2026-11-13)
- [L-fd378fc9] LAMMPS aborts 'Requested GPU with id 3 but only 1GPU(s) available!' -> -k on g 4 under flux run -g1 -> -k on g 1 (date not recorded in source; converted 2026-11-13)
- [L-939994fb] LAMMPS annotated build 'static declaration of finalize follows non-static declaration' / 0-byte traces rc=0 -> dftracer.h global finalize() vs main.cpp static finalize() -> rename the LAMMPS helper (lmp_local_finalize) at definition and 7 call sites (date not recorded in source; converted 2026-11-13)
- [L-a4004eda] LAMMPS annotated KOKKOS files fail to compile -> annotator put host macros in KOKKOS_INLINE_FUNCTION/KOKKOS_FUNCTION bodies -> strip them after every annotate call (date not recorded in source; converted 2026-11-13)
- [L-79f2f2ca] LAMMPS neighbor.cpp ~20 compile errors -> include placed after mid-file #include (line 796, macros from 115) -> move include after the first #include (date not recorded in source; converted 2026-11-13)
- [L-e7d4b3f3] LAMMPS trace 89% setup events -> lattice2box (2,721,792) and create_atom (1,024,000) run per lattice point/atom -> exclude them with the domain per-atom helpers (date not recorded in source; converted 2026-11-13)
