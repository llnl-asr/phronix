# Lessons: software_papi

- [L-8764b3e8] 5-name set on MI300A (BR_MSP, BR_PRC, FP_OPS, FP_INS, FMA_INS) multiplexed and PAPI_BR_PRC vanished; exit 0 -> Three members are derived presets costing >= 2 hardware counters against a 5-counter budget -> Size sets by probing args.multiplex, not by counting names; split into per-family runs (undated)
- [L-5ecfc01c] Same 4-name set multiplex=1 on login node, 0 on compute node -> multiplex depends on the machine the counters are programmed on -> Probe on a compute node inside the allocation (undated)
- [L-ee7b0c10] Analyses filtering cat CACHE/FLOP/BRANCH/TLB/INSTRUCTION/CYCLE read zero -> dftracer switched to family-grouped events under cat == 'papi' -> Filter cat == 'papi' and use the event name as the family (undated)
- [L-b6d1883b] Long runs crash in gotcha_get_wrappee at finalize; short runs fine -> PAPI sampler stopped after posix unbind; PAPI_read's read(2) hits a removed wrapper -> Finalize the sampler first; check DFTracerCore::finalize() on the branch; count zero-byte traces and end events (undated)
- [L-58dcdbfe] SIGSEGV in PAPI_library_init; build probe falls back to two counters -> papi/7.3.0.1 rocp_sdk component ABI-incompatible with installed ROCm on Tuolumne -> Pin papi/7.2.0.2 (undated)
- [L-6570d204] Asking for all 17 Sapphire Rapids presets: multiplexed, 2 silently missing -> Only 10 fit at once (DFTRACER_PAPI_FITTING_COUNTERS 10); derived presets expand -> Group-aligned 2-run partition (10 + 7), both exact (undated)
- [L-fc85624d] 4-name mixed set (TOT_INS, TOT_CYC, FP_OPS, DP_OPS) multiplexed on Sapphire Rapids while 10-name set was exact -> Cross-group mixtures with derived presets overflow unpredictably -> Use group-aligned sets and probe each (undated)
