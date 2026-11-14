# What worked: workload_ygm_bench

## ygm_bench/build/annotated
`cmake -S ygm-bench -B build -DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source` (GNU toolchain), INIT/FINI added to each bench
main(); `ldd <binary> | grep dftracer` shows the dftracer link via ygm::ygm.

## ygm_bench/smoke
1 node / 4 ranks: `around_the_world_ygm -n 50 -t 2 -p`, `barrier_bench -b 500 -a 0 -t 2 -p`; 8,222 events in a rank file,
CPP_APP 3686, p2p 3361.

## ygm_bench/scaled/tuolumne
2026-08-04: 4 nodes x 32 ranks/node, default YGM buffers, `DFTRACER_ENABLE_AGGREGATION=1 DFTRACER_AGGREGATION_TYPE=SELECTIVE
DFTRACER_AGGREGATION_FILE=<rules.yaml> DFTRACER_TRACE_INTERVAL_MS=5000` (rules: inclusion "dur < 1000"),
`around_the_world_ygm -n 5600 -t 1 -p` -> 660.04 s, 716,800 hops, 55 MB trace across 128 rank files.

## tool:workload_ygm_bench_recipe
Renders the above as JSON; `workload_ygm_bench_check` rules on a proposed command list.
