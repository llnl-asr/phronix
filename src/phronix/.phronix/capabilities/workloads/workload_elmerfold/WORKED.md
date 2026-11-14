# What worked: workload_elmerfold

## elmerfold/env/build
`./setup-env.sh --use-rocm7 --no-managed-python <venv on Lustre>` (rocm/7.2.1, PrgEnv-gnu, uv venv ~6 GB); when emf_data (private) fails:
`uv pip install -e ./ems`, cppdbfixer, `patches/openmm1.patch` + `openmm2.patch` into site-packages; verify
`python -c "import ems.metrics, cppdbfixer, openfold, ofcpp, relaxcpp, openmm, torch"`.

## elmerfold/run/launch
`module load mpifileutils/0.11.1` in the submitting shell; `python utils/gen_launch_script.py --config configs/tuolumne_test.yaml --inchunks
$LUSTRE_ROOT/lbann/elmerfold/splits/1n_10s --submit-script <src>/monomer-structure-prediction/submit_smsp.sh --output-dir <run>/output
--env-dir <venv> --timing-dir test_timing --log-dir test_logs --prestage-script <src>/monomer-structure-prediction/prestage_check.sh -- run.sh`;
`flux batch -t 1h --queue pdebug run.sh`: 2 nodes (chunks + 1), ~520 s, `<run>/output/chunk_000000/<seq_id>.tar`.

## elmerfold/provenance/annotate
23 entity types, 16 activities; inference_request entity as driver->server edge; per-process init in driver main(), executor_worker_init
and server initialize(); 1n_10s: 240 entities, 181 activities, 761 edges, 0 dangling, 526 s vs 520 s, byte-identical outputs.

## elmerfold/live/launch
Live runs: gen_launch_script with --src-dir provenance/source and a live wrapper as --submit-script, nodes = chunks + 1, one bulksubmit line,
batch plan dry run, then the live run tool with queue pbatch and limit 43200 (2026-11-12).

## tool:workload_elmerfold_recipe
Renders the env/launch recipe as JSON; `workload_elmerfold_check` rules on proposed commands.
