# What worked: workload_1000genome

## 1000genome/pmc/run
Pegasus 5.0.7 + PMC built from source, Condor planning-only (software_pegasus); workflow scoped with `daxgen.py -i <num_individuals_jobs>`
and prepare_input.sh to a ~10-20 min run; 4-node PMC DAG, 46/46 tasks succeed.

## 1000genome/annotate
python_annotate_project on individuals.py, individuals_merge.py, sifting.py, mutation_overlap.py, frequency.py (not daxgen.py or the
*_mpi.py variants); module-level tar blocks wrapped with `with DFTracerFn(...):`; 5/5 files, 38/38 functions.

## 1000genome/optimize/individuals
`IND_ROW_PRECOMPUTE=1` + `IND_TAR_STREAM=1` (both default off) and removal of the dead `chrp_data` accumulator: 90.65 s -> 0.47 s per task,
verified by per-member md5 of the extracted output tar (2504/2504) and `diff -rq` over the per-individual files; DAG 316.5 s -> 244.7 s (2026-07-26).

## tool:workload_1000genome_recipe
Renders the above as JSON; `workload_1000genome_check` rules on proposed commands.
