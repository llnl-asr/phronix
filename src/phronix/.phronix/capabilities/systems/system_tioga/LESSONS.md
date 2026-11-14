# Lessons: system_tioga

- [L-f51d97b2] Job submitted to pall sits S forever -> pall submission enabled but scheduling stopped; flux queue list hides it -> Check flux queue status; use pdebug (undated)
- [L-6762f05a] Sweep cells needing >= 4 nodes unrunnable for > 16 h -> Most nodes drained: pdebug had 2 of 8 free, pci 0 of 4 -> Check flux resource list; size to free nodes; stop rather than chain impossible allocations (undated)
- [L-b177c6e2] flux-alloc: ERROR: queue "pllm" not valid for user -> Account not authorized for pllm despite it appearing enabled -> Throwaway flux alloc to learn authorization; use pdebug/pci (undated)
- [L-34ade202] App job at max ppn never scheduled (sat S forever) -> dftracer_service holds one core per node; 64/ppn cores per rank requests all 64 -> floor((cores_per_node - 1) / max_ppn): ppn=8 -> 7 cores (undated)
- [L-2a680bdd] Tuolumne PAPI partition requests missing presets and mis-sizes sets -> tioga has 27 presets (5 derived) vs 30 (12 derived); no L2_TCM/L2_TCH/FMA_INS -> Derive from tioga papi_avail; probe args.multiplex == 0 (undated)
- [L-da4b71de] Traced multi-rank GPU runs SIGSEGV at >= 3 ranks, reproducible 3/3, invisible under gdb -> BufferManager published before initialize(); rocprofiler thread pool flushes into null config -> dftracer BufferManager ready atomic guarding log_*_event (undated)
- [L-c2f8e4da] Offload kernels do not run from a Tuolumne binary -> Built for gfx942; tioga MI250X is gfx90a -> Rebuild targeting gfx90a (undated)
- [L-44d0bb72] Application output missing while traces read fine -> dataset symlink onto /p/lustre5 (Tuolumne), not mounted on tioga -> Use /p/lustre1/$USER; check ls -d /p/lustre* (undated)
- [L-90095460] dftracer_service start under flux run never returns -> Service start blocks the flux run step -> flux submit detached; poll per-host pid files (undated)
- [L-8ea66efb] Zero power events with DFTRACER_BUILD_VARIORUM=AUTO -> System variorum RPM reports _ERROR_VARIORUM_UNSUPPORTED_PLATFORM -> DFTRACER_BUILD_VARIORUM=ALWAYS; verify a gpu/power event lands (undated)
- [L-c3356e81] corrupted size vs. prev_size in fastbins at service teardown -> librocm_smi64 .so.1 (libhwloc) and .so.7 (libvariorum) both mapped -> None needed: post-flush, no data lost; HWLOC_COMPONENTS=-rsmi does not help (undated)
