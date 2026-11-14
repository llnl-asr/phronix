"""Elmerfold (OpenFold monomer structure prediction) provenance annotation facts that have one right answer, plus (v2, merged
from dftracer-agents' workload-elmerfold skill) the env-build / launch recipe as structured data (workload_elmerfold_recipe)
and a deterministic check of a proposed command list against its rules (workload_elmerfold_check)."""
import json
import re

TYPE_LIMIT = 31

BATCH = {
    "functions": {
        "load_and_merge_msas": {"capture": {"outputs": {"sequence_length": "<sequence length>", "merged_msa_bytes": "<merged msa size in bytes>"}}},
        "template_featgen": {
            "attributes": ["num_templates"],
            "outputs": ["num_templates"],
            "note": "num_templates comes from the return value of generate_template_features",
        },
        "load_inputs": {"capture": {"inputs": {"input_chunk_file": "<path of the input chunk file>"}}},
    },
    "activities": {
        "subprocess_finish": {
            "mode": "patch",
            "target": "SubprocessTask.on_finish (ems/src/ems/task.py base hook)",
            "generates": "pipeline_task",
            "attributes": ["returncode", "error"],
            "answers": "which sequences failed the template/filter step",
        },
        "stage_setup": {
            "mode": "statement",
            "after": "self._stage_dir = stage_dir in OF2StructurePredictionPipeline.__init__",
            "generates": "stage_area",
            "attributes": ["mount_point", "mount_device", "mount_fstype"],
            "attribute_source": "/proc/mounts entry covering stage_dir",
            "inputs": ["user", "host"],
            "note": "identifies the Rabbit mount",
        },
    },
}


def _flat(spec) -> str:
    return json.dumps(spec, sort_keys=True)


# ---------------------------------------------------------------- v2: env build / launch recipe (dftracer-agents workload-elmerfold)
CAP = "workload_elmerfold"

RECIPE = {
    "app": "Elmerfold",
    "what": "LLNL OpenFold monomer-structure-prediction campaign workflow: predicts protein structures for MGnify sequences",
    "source": "lbann/openfold (LC GitLab), monomer-structure-prediction/",
    "driver": "monomer-structure-prediction/ems_structure_prediction.py, launched per input chunk by submit_smsp.sh; GPU inference in "
              "a separate server process (openfold_server_ems.py)",
    "reference_data": "$LUSTRE_ROOT/lbann/elmerfold",
    "systems": ["tuolumne"],
    "env_build": {
        "command": "./setup-env.sh --use-rocm7 --no-managed-python <venv>",
        "loads": ["rocm/7.2.1", "PrgEnv-gnu"],
        "builds": ["uv venv (no pip inside)", "hmmer 3.3.2", "hh-suite 3.3.0", "MMseqs2", "OpenMM", "ofcpp", "relaxcpp",
                   "kalign (from the site Lustre copy)"],
        "venv_location": "Lustre, not NFS (partial NFS venv 16 GB before torch finished; finished Lustre venv ~6 GB)",
        "retry": "rm -rf source/build/ first: the script refuses to run if it exists",
        "private_repo_fallback": [
            "pip install git+ssh://.../openfoldcollab/emf_data.git fails without access: nothing imports emf_data, skip it",
            "uv pip install -e ./ems",
            "uv pip install cppdbfixer (git+ssh, needed by the relaxation code)",
            "apply patches/openmm1.patch and patches/openmm2.patch into site-packages",
            "python -c \"import ems.metrics, cppdbfixer, openfold, ofcpp, relaxcpp, openmm, torch\"",
        ],
    },
    "launch": {
        "modules": ["mpifileutils/0.11.1 (0.12.0 is broken; dbcast must be on PATH in the submitting shell)"],
        "generate": "python utils/gen_launch_script.py --config configs/tuolumne_test.yaml --inchunks $LUSTRE_ROOT/lbann/elmerfold/splits/1n_10s "
                    "--submit-script <src>/monomer-structure-prediction/submit_smsp.sh [--src-dir <src>] --output-dir <run>/output "
                    "--env-dir <venv> --timing-dir test_timing --log-dir test_logs "
                    "--prestage-script <src>/monomer-structure-prediction/prestage_check.sh -- run.sh",
        "submit": "flux batch -t 1h --queue pdebug run.sh",
        "run_sh": "self-contained: #flux: --nodes 2 --exclusive plus a 1300 GiB Rabbit XFS #DW jobdw staging area; one node drained as launch node "
                  "(nodes = chunks + 1)",
        "src_dir": "--src-dir selects the source tree the job runs (point it at an instrumented copy)",
        "timing_1n_10s": "~5 min broadcasting reference data (pdb70 87 GB, mmCIF 309 GB) to Rabbit, ~3 min prediction, ~520 s total",
        "output": "<run>/output/chunk_000000/<seq_id>.tar",
        "noise": "spindle_be: No route to host lines at job teardown",
    },
    "task_dag": ["init", "load (load_and_merge_msas: jackhmmer + hhblits MSA members via pickle indices)", "filter (mmseqs filtera3m)",
                 "filter-cleanup (deletes merged MSA, up to ~2.4 GB)", "featgen", "of2templates (hhsearch vs pdb70)",
                 "templatefeat (allow_failure)", "model_3_ptm (no templates)", "model_1_ptm (templates, allow_failure)",
                 "in-server relax", "best (max mean pLDDT)", "save (zstd members into <seq_id>.tar)", "cleanup",
                 "parallel OF3 chain: a3m-to-sto -> of3-hmmbuild -> of3templates (pdb_seqres)"],
    "tar_contents": ["all_pred_metric.csv", "best_structure_relaxed.pdb", "filtered a3m", "hhsearch_output.hhr", "hmm_output.sto",
                     "extra_structures/<per-model relaxed PDBs>"],
    "process_layout": "driver (main loop + ImmediateTasks), process pool (FunctionTasks), GPU inference server(s); subprocess tasks run "
                      "mmseqs/hhsearch/hmmbuild; per-process instrumentation must initialize in driver main(), executor_worker_init and "
                      "the server's initialize()",
    "provenance": {
        "spec": "23 entity types, 16 activities; artifacts: best structure + metrics, per-model structures, filtered MSA, template hits/alignment, per-sequence tar",
        "ids": "sequence-scoped seq_id; per-model <seq_id>/<model>; reference files basename@size:mtime; run config preset:<config_preset>",
        "driver_server_edge": "inference_request entity (<seq_id>/<model>) generated in a ServerTask subclass start(), used in the server run_inference",
        "result_1n_10s": "29 trace files, 240 entities, 181 activities, 761 edges, 0 dangling; 526 s vs 520 s untraced; outputs byte-identical",
    },
    "variants": {},
}

RULES = [
    {"id": "dbcast_module", "require": r"mpifileutils/0\.11\.1", "when": r"flux\s+batch|run\.sh",
     "why": "run.sh exits in ~30 s with 'dbcast not found, load mpifileutils' unless dbcast is on PATH in the submitting shell",
     "fix": "module load mpifileutils/0.11.1 before flux batch (flux batch propagates the env)"},
    {"id": "no_mpifileutils_012", "forbid": r"mpifileutils/0\.12",
     "why": "mpifileutils 0.12.0 is broken (the app pins 0.11.1 in generate_campaign_scripts.sh)", "fix": "module load mpifileutils/0.11.1"},
    {"id": "no_emf_data", "forbid": r"pip\s+install\s+.*emf_data",
     "why": "emf_data is a private openfoldcollab repo; the install fails without access and nothing imports it",
     "fix": "skip it: uv pip install -e ./ems, cppdbfixer, then the openmm patches"},
    {"id": "no_pip_in_uv_venv", "forbid": r"^(?!.*\buv\b).*\bpip\s+install\b(?!.*emf_data)",
     "why": "setup-env.sh creates a uv venv with no pip inside", "fix": "use uv pip install"},
    {"id": "setup_env_rocm7", "require": r"setup-env\.sh\s+.*--use-rocm7", "when": r"setup-env\.sh",
     "why": "the verified env build is setup-env.sh --use-rocm7 --no-managed-python (rocm/7.2.1, PrgEnv-gnu)",
     "fix": "./setup-env.sh --use-rocm7 --no-managed-python <venv on Lustre>"},
    {"id": "venv_not_nfs", "forbid": r"setup-env\.sh\b.*\s(?:~|\$HOME|/g/g\d*|/usr/work)",
     "why": "an NFS venv grew to 16 GB before torch finished; the Lustre venv is ~6 GB", "fix": "put the venv on Lustre"},
]


# ---------------------------------------------------------------- shared logic (same in every workload_* capability)
def _commands(commands):
    if isinstance(commands, str):
        s = commands.strip()
        if s.startswith("[") or s.startswith("{"):
            try:
                commands = json.loads(s)
            except ValueError:
                commands = s.splitlines()
        else:
            commands = s.splitlines()
    if isinstance(commands, dict):
        flat = []
        for v in commands.values():
            flat += v if isinstance(v, list) else [v]
        commands = flat
    return [str(c) for c in (commands or []) if str(c).strip()]


def _check(commands):
    cmds = _commands(commands)
    if not cmds:
        return {"status": "inconclusive", "checks": [{"check": "input", "ok": False, "detail": "no commands given",
                                                      "fix": f"pass the proposed commands (e.g. {CAP}_recipe's configure/build/run)"}]}
    text = "\n".join(cmds)
    out = []
    for r in RULES:
        if "forbid" in r:
            hit = [c for c in cmds if re.search(r["forbid"], c)]
            out.append({"check": r["id"], "ok": not hit, "detail": (r["why"] + " | offending: " + hit[0][:160]) if hit else "ok",
                        "fix": r["fix"] if hit else ""})
        else:
            if r.get("when") and not re.search(r["when"], text):
                continue
            ok = bool(re.search(r["require"], text))
            out.append({"check": r["id"], "ok": ok, "detail": "ok" if ok else r["why"], "fix": "" if ok else r["fix"]})
    return {"status": "pass" if all(c["ok"] for c in out) else "fail", "checks": out}


def _recipe(variant=""):
    rec = dict(RECIPE)
    v = (variant or "").strip()
    if v:
        if v not in RECIPE.get("variants", {}):
            return {"status": "error", "error": f"unknown variant {v!r}", "variants": sorted(RECIPE.get("variants", {}))}
        rec["variants"] = {v: RECIPE["variants"][v]}
    return {"status": "ok", "capability": CAP, "recipe": rec,
            "rules": [{"id": r["id"], "why": r["why"], "fix": r["fix"]} for r in RULES]}


def register(mcp):
    @mcp.tool()
    def workload_elmerfold_recipe(variant: str = "") -> dict:
        """Predictor: the Elmerfold env-build and launch recipe dftracer-agents verified on Tuolumne: setup-env.sh (uv, ROCm 7.2.1,
        PrgEnv-gnu) and the private-repo fallback, gen_launch_script -> run.sh -> flux batch with mpifileutils/0.11.1 (dbcast),
        Rabbit staging, the per-sequence task DAG, process layout and the verified provenance numbers. variant: optional (none
        defined; any value returns an unknown-variant error). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_elmerfold_check(commands: list) -> dict:
        """Validator: check a proposed Elmerfold env-build/launch command list against the skill's rules (mpifileutils/0.11.1
        loaded before flux batch, never 0.12, no emf_data install, uv pip not pip, setup-env.sh --use-rocm7, venv not on NFS).
        commands: list of shell lines (or a newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

    @mcp.tool()
    def elmerfold_gap_batch() -> dict:
        """The Elmerfold 23-gap batch spec changes to apply to the annotation spec: function capture/outputs/attributes and the two new
        activities (subprocess_finish, stage_setup). Use before annotate_spec for an elmerfold app. The spec is always sent whole to
        annotate_spec, never as a patch. Returns {batch, notes}."""
        return {"batch": BATCH, "notes": [
            "send the whole spec to annotate_spec every time",
            "types are cut at 31 chars in traces: keep entity/activity type names unique within 31 chars",
            "gen_launch_script.py derives --nodes as chunks + 1 (one launch node)"]}

    @mcp.tool()
    def elmerfold_nodes(chunks: int) -> dict:
        """Nodes gen_launch_script.py requests for a number of input chunks: chunks + 1 (the extra one is the drained launch node).
        chunks: number of input chunks (>=1). Returns {chunks, nodes}."""
        if chunks < 1:
            raise ValueError("chunks must be >= 1")
        return {"chunks": chunks, "nodes": chunks + 1}

    @mcp.tool()
    def elmerfold_type_cut(name: str) -> dict:
        """How a type name appears in traces: cut at 31 characters. Use to check two types stay distinct in a query.
        name: entity or activity type. Returns {name, in_trace, cut}."""
        return {"name": name, "in_trace": name[:TYPE_LIMIT], "cut": len(name) > TYPE_LIMIT}

    @mcp.tool()
    def elmerfold_spec_validate(spec: str) -> dict:
        """Validator: a whole annotation spec (JSON text) carries every gap-batch item. Names the missing ones.
        spec: JSON text of the spec. Returns {ok, missing, too_long_types}."""
        s = json.loads(spec)
        text = _flat(s)
        need = ["load_and_merge_msas", "template_featgen", "num_templates", "subprocess_finish", "on_finish", "pipeline_task",
                "returncode", "stage_setup", "stage_area", "mount_point", "mount_device", "mount_fstype", "load_inputs"]
        missing = [n for n in need if n not in text]
        types = []

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("type", "entity_type", "generates") and isinstance(v, str):
                        types.append(v)
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(s)
        long = sorted({t for t in types if len(t) > TYPE_LIMIT})
        return {"ok": not missing and not long, "missing": missing, "too_long_types": long,
                "fix": "add the missing items from elmerfold_gap_batch; shorten types to 31 chars" if missing or long else ""}
