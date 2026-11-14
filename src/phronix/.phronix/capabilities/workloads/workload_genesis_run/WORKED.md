# What worked: workload_genesis_run

## genesis/plan/inputs
`curl -sL https://raw.githubusercontent.com/llnl/ice4hpc_data/main/data/merged.txt -o merged.txt; grep ",<app>," merged.txt | sed 's/^[^,]*,[^,]*,<app>,"//; s/",[0-9.]*$//' | sort -u > genesis/<system>/inputs.txt`; all unique args swept (laghos 186 -> 3348 runs, ~380 node-hours).

## genesis/sweep/run-flux
Service `flux submit -N<n> -n<n> -c1 --requires=host:<csv> --setattr=exclusive=false <svc> start <dir>` (poll pid files) -> `flux run` the app on the same hosts from `genesis/<system>/build/<exe>` with cwd in `dataset/` -> `flux submit` service stop on the same hosts; cores/rank floor((cores_per_node-1)/max_ppn).

## genesis/sweep/run-slurm
Long-lived service step `srun -N$N -n$N -c1 --nodelist="$SLICE" --overlap bash -c '<start>; wait flag; <stop>; wait for non-empty trace' &`, app `srun --nodelist="$SLICE" --overlap ...`, then `touch "$FLAG"; wait`. Chain with `genesis_slurm_chain.sh <part> <nodes> <min> <depth> <name>`.

## genesis/sweep/chain-flux
`flux batch -q <Q> -N<N> -t <short T> --bank=<bank> --job-name=genesis-<grp> --output=<G>/artifacts/batch_<grp>_{{id}}.log --dependency=afterany:<prev> <G>/worker_<grp>.sh`, worker takes `flock -n` on `${STATE}.lock`.

## genesis/sweep/checkpoint
`<case>_N<n>_ppn<p>_<set> ok dt=<s>` after validation only; progress `grep -v SKIPPED "$STATE" | awk '{print $1}' | sort -u | wc -l`; merge `cat state_* | sort -u > state_all.new && mv` inside the worker at startup.

## genesis/publish/order
run_<set>.json after each run -> leaf seals -> dcp raw/ to `<archive>/<app>/<system>/<case>/nodes_<N>/ppn_<P>/raw` -> verify regular-file bytes+count (+dcmp) -> delete workspace raw/ (ARCHIVED symlink) -> `GENESIS_ROOT=<archive> genesis_compact.sh` in place -> COMPACTION_NOT_RUN.md if it fails -> `<archive>/chgperm.sh` -> `genesis_validate_leaf.py <archive> --sets=N` (343/343 on amg/tuolumne).

## genesis/compact/parallel
`flux run -N2 -n16 -o exit-timeout=none genesis_compact.sh` dealing leaves round-robin on FLUX_TASK_RANK (~20x serial); `grep -a 'Verification: PASSED'`; hardlink staging inside the leaf.

## genesis/validate/fast
Category slice + substring prefilter ('"dftracer"', 'multiplex', 'PAPI_', 'dft_cnt') + ProcessPoolExecutor per trace file: 1.36 B-event cell 57-91 min -> 68 s, byte-identical JSON vs the slow validator.

## tool:workload_genesis_run_matrix
`workload_genesis_run_matrix(n_inputs=186, node_scales="1,2,4", ppns="1,2,4", papi_sets="a,b")` -> total_runs 3348 (the laghos figure).
