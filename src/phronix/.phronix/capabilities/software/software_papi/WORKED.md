# What worked: software_papi

- [tool:papi_probe] Run the app a few seconds at toy size (miniFE nx=64, 1 rank, ~1 s) per candidate set on a compute node; EXACT iff every event has args.multiplex == 0 and every requested PAPI_* key (excluding _delta) appears.
- [tool:papi_run_per_set] `export DFTRACER_ENABLE_PAPI_TRACING=1; export DFTRACER_PAPI_EVENTS=PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_L1_DCM; export DFTRACER_PAPI_SAMPLE_INTERVAL_MS=100`, one run per set, PAPI_TOT_CYC in every set for per-cycle normalization.
- [sapphire_rapids/papi/partition] Set1 (10): PAPI_BR_UCN,PAPI_BR_CN,PAPI_BR_TKN,PAPI_BR_NTK,PAPI_BR_MSP,PAPI_BR_PRC,PAPI_BR_INS,PAPI_TOT_INS,PAPI_TOT_CYC,PAPI_REF_CYC; Set2 (7): PAPI_FP_INS,PAPI_VEC_INS,PAPI_FP_OPS,PAPI_SP_OPS,PAPI_DP_OPS,PAPI_VEC_SP,PAPI_VEC_DP; both multiplex=0, nothing missing (PAPI 5.6.0.0).
