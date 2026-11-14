---
name: workload_elmerfold
description: Elmerfold (LBANN OpenFold monomer-structure-prediction campaign workflow on Tuolumne) - env build via setup-env.sh (uv, ROCm 7.2.1, PrgEnv-gnu) and the private-repo step that fails, gen_launch_script -> run.sh -> flux batch with Rabbit staging and dbcast (mpifileutils/0.11.1), the per-sequence task DAG, process layout, the verified provenance recipe, and the provenance annotation 23-gap batch (MSA, templates, subprocess failures, Rabbit stage area, input chunk), launch node count, 31-char type cut. Load for any elmerfold/openfold session, "dbcast not found, load mpifileutils", emf_data install failure, or fixing its query gaps.
---
Cross-references: [[prov_gaps]], [[prov_annotate]], [[capability_builder]], [[system_tuolumne]], [[system_tuolumne_rabbit]], [[software_flux]], [[software_mpifileutils]], [[software_rocm]], [[tools_dftracer]]

# workload_elmerfold

Elmerfold predicts protein structures for MGnify sequences at campaign scale. Source: `lbann/openfold` (LC GitLab). The workflow
driver is `monomer-structure-prediction/ems_structure_prediction.py`, launched per input chunk by `submit_smsp.sh`; GPU inference
runs in a separate server process (`openfold_server_ems.py`). Reference data lives under `$LUSTRE_ROOT/lbann/elmerfold`.

Version 2 merges dftracer-agents' `workload-elmerfold` skill (env build, launch, task DAG, process layout, verified provenance
recipe) into this capability: earlier this skill kept only the provenance annotation and reused that skill by reference; its
facts now live here. `workload_elmerfold_recipe` renders the build/launch recipe and `workload_elmerfold_check` rules on a
proposed command list; `elmerfold_gap_batch`, `elmerfold_nodes`, `elmerfold_type_cut` predict the annotation and
`elmerfold_spec_validate` validates the spec.

## Rules

### Env build
`./setup-env.sh --use-rocm7 --no-managed-python <venv>`: loads `ml rocm/7.2.1 PrgEnv-gnu`, creates a **uv** venv (no `pip`
inside), builds hmmer 3.3.2, hh-suite 3.3.0, MMseqs2, OpenMM, ofcpp, relaxcpp, and pulls kalign from the site Lustre copy.
- Put the venv on Lustre, not NFS: the partial NFS venv was 16 GB before torch finished installing; the finished Lustre venv is ~6 GB.
- The script refuses to run if `source/build/` exists: remove it before a retry.
- `pip install git+ssh://.../openfoldcollab/emf_data.git` fails for accounts without access to that GitLab project. Nothing in the
  openfold tree imports `emf_data`; run the remaining steps by hand: `uv pip install -e ./ems`, `cppdbfixer` (git+ssh, needed by
  the relaxation code), then `patches/openmm1.patch` and `openmm2.patch` into site-packages. Verify with
  `python -c "import ems.metrics, cppdbfixer, openfold, ofcpp, relaxcpp, openmm, torch"`.

### Launching a run
```
python utils/gen_launch_script.py --config configs/tuolumne_test.yaml \
  --inchunks $LUSTRE_ROOT/lbann/elmerfold/splits/1n_10s \
  --submit-script <src>/monomer-structure-prediction/submit_smsp.sh [--src-dir <src>] \
  --output-dir <run>/output --env-dir <venv> --timing-dir test_timing --log-dir test_logs \
  --prestage-script <src>/monomer-structure-prediction/prestage_check.sh -- run.sh
flux batch -t 1h --queue pdebug run.sh
```
- `run.sh` is self-contained: `#flux: --nodes 2 --exclusive` plus a 1300 GiB Rabbit XFS `#DW jobdw` staging area; one node is
  drained as the launch node.
- **`dbcast` must be on PATH in the submitting shell** (`flux batch` propagates the env). Without it run.sh exits in ~30 s with
  `dbcast not found, load mpifileutils`. Load **`mpifileutils/0.11.1`**: the app pins it because 0.12.0 is broken
  (`monomer-structure-prediction/generate_campaign_scripts.sh`).
- `--src-dir` selects the source tree the job runs (use it to point at an instrumented copy).
- `1n_10s` (10 sequences): ~5 min broadcasting reference data (pdb70 87 GB, mmCIF 309 GB) to Rabbit, ~3 min of prediction;
  ~520 s total. Output: `<run>/output/chunk_000000/<seq_id>.tar`.
- `gen_launch_script.py` derives `--nodes` as chunks + 1 (launch node): `elmerfold_nodes`.

### Per-sequence task DAG
Defined in `OF2StructurePredictionPipeline._build_tasks`: `init` -> `load` (`load_and_merge_msas`: jackhmmer + hhblits MSA
members out of shared archives via pickle indices) -> `filter` (mmseqs filtera3m) -> `filter-cleanup` (deletes the merged MSA,
up to ~2.4 GB) -> `featgen` (MSA feature bundle) and `of2templates` (hhsearch vs pdb70) -> `templatefeat` (allow_failure) -> two
GPU inferences, `model_3_ptm` (no templates) and `model_1_ptm` (templates, allow_failure) -> in-server relax -> `best` (max mean
pLDDT) -> `save` (zstd members into `<seq_id>.tar`) -> `cleanup`. In parallel, the OF3 template chain: `a3m-to-sto` ->
`of3-hmmbuild` -> `of3templates` (pdb_seqres).

Tar contents: `all_pred_metric.csv`, `best_structure_relaxed.pdb`, the filtered a3m, `hhsearch_output.hhr`, `hmm_output.sto`, and
both per-model relaxed PDBs under `extra_structures/`.

### Process layout
Three kinds of process touch data: the driver (main loop + ImmediateTasks), a process pool running FunctionTasks, and the GPU
inference server(s). Subprocess tasks run external binaries (mmseqs, hhsearch, hmmbuild). Any per-process instrumentation must
initialize in all three: driver `main()`, `executor_worker_init`, and the server's `initialize()`.

### Provenance recipe (verified, dftracer provenance mode)
Spec: 23 entity types, 16 activities; artifacts = best structure + metrics, per-model structures, filtered MSA, template
hits/alignment, per-sequence tar. See dftracer-provenance CASES.md "Structure prediction - elmerfold" for the type/id table.
- Ids: sequence-scoped types use `seq_id`; per-model types use `<seq_id>/<model>`; reference files `basename@size:mtime`; run
  config `preset:<config_preset>` when no config JSON is passed (the production default).
- The driver->server edge is the `inference_request` entity (`<seq_id>/<model>`), generated in a `ServerTask` subclass's
  `start()` and used in the server's `run_inference`.
- Results on `1n_10s`: 29 trace files, 240 entities, 181 activities, 761 edges, 0 dangling; run time 526 s vs 520 s untraced; tar
  members and metrics byte-identical to the plain run.

### Provenance annotation: the 23-gap batch (moirai)
- Apply the batch from `elmerfold_gap_batch` (evidence: user asked to improve coverage for all 23 open gaps):
  - `load_and_merge_msas`: `capture.outputs` of sequence length and merged MSA bytes.
  - `template_featgen`: attribute and output `num_templates`, taken from the return value of `generate_template_features`.
  - activity `subprocess_finish`: patch `SubprocessTask.on_finish` (base hook, `ems/src/ems/task.py`), generating
    `pipeline_task` entities with `returncode` and `error`; this makes "which sequences failed the template/filter step" answerable.
  - activity `stage_setup`: statement right after `self._stage_dir = stage_dir` in `OF2StructurePredictionPipeline.__init__`,
    generating a `stage_area` entity with `mount_point`, `mount_device`, `mount_fstype` read from `/proc/mounts`, plus `user` and
    `host` inputs (the Rabbit mount).
  - `load_inputs`: capture the input chunk file.
- Types are cut at 31 characters in traces: check with `elmerfold_type_cut`; keep type names distinct within 31.
- The spec is always sent WHOLE to `annotate_spec`; run `elmerfold_spec_validate` on it first.

## Constraints
- Capturing must never change the app or fail it: wrap `/proc/mounts` reads and return-value inspection in try/except.
- Source tree is read-only; annotate the pipeline copy.
- Ask before re-running the smoke or baseline.
- The uv venv has no pip: use `uv pip install`.

## Corner cases
- `on_finish` fires for every subclass task; the patch is on the base class, so do not also patch subclasses.
- `/proc/mounts` may list several matches: take the longest mount_point that prefixes the stage dir.
- num_templates may be 0: record 0, not absent.
- The `spindle_be: No route to host` lines at job teardown are noise.
- `run.sh` exits in ~30 s with `dbcast not found, load mpifileutils`: load `mpifileutils/0.11.1` in the submitting shell.
- `setup-env.sh` refuses to run: a `source/build/` from a previous attempt exists; remove it.
- emf_data git+ssh install fails (no access to openfoldcollab): skip it, nothing imports it.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Validator `elmerfold_spec_validate`: for each name in `missing`, add it from `elmerfold_gap_batch` to the whole spec; for
  `too_long_types`, shorten to 31 chars; validate again, then `annotate_spec`.
- Validator `workload_elmerfold_check`: `dbcast_module` / `no_mpifileutils_012` -> `module load mpifileutils/0.11.1` before
  `flux batch`; `no_emf_data` -> drop the emf_data install and run the by-hand steps; `no_pip_in_uv_venv` -> `uv pip install`;
  `setup_env_rocm7` -> `./setup-env.sh --use-rocm7 --no-managed-python <venv>`; `venv_not_nfs` -> venv on Lustre; `input`
  (inconclusive) -> pass the commands. Then `workload_elmerfold_recipe` and the check again; the same failure twice stops the loop.

## Self-heal
- Tool failed: follow capability_builder's Self-heal; `lesson_search` the error first.
- Gap still shown after re-run: check the annotated copy contains the patch, then re-collect with `gap_collect`.
- Env build or launch fails: match it to Corner cases and LESSONS.md; if a recipe fact is wrong, `capability_update` this capability.

## Self-learn
- Anything new explored here (workload, software, tool, system) becomes a capability: capability_builder, Rules.
- Each closed Elmerfold gap adds its exact capture expression here.
- Capability needed (from L-67e71dd0): `elmerfold_live_script(pipeline, inchunks, queue, limit)` that calls the generator, checks
  nodes = chunks + 1 and the wrapper STAGE tag, and returns the batch script path for moirai_live_run.

## What works
- Env: `./setup-env.sh --use-rocm7 --no-managed-python <lustre venv>`, emf_data skipped, `uv pip install -e ./ems`, cppdbfixer,
  openmm patches; the import check passes.
- Run `1n_10s` on Tuolumne: gen_launch_script + `flux batch -t 1h --queue pdebug run.sh` with mpifileutils/0.11.1: ~520 s.
- Provenance on `1n_10s`: 29 trace files, 240 entities, 181 activities, 761 edges, 0 dangling; 526 s vs 520 s; byte-identical outputs.
- Live runs at 32 and 64 nodes (2026-11-12, see LESSONS L-67e71dd0): nodes = chunks + 1 (32 and 65), pbatch, -t 720.
