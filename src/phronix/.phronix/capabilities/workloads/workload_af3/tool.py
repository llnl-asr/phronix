"""workload_af3: AlphaFold3 (AF3, JAX/XLA inference on ROCm, Python) facts dftracer-agents' workload-af3 skill verified on
Tuolumne - inputs, env, annotation pitfalls and the confirmed bucket optimization - as structured data (predictor), and a
deterministic check of a proposed recipe or command list against that skill's rules (validator). Nothing here runs."""
import json
import re

CAP = "workload_af3"

DEFAULT_BUCKETS = "256,512,768,1024,1280,1536,2048,2560,3072,3584,4096,4608,5120"
TUNED_BUCKETS = "256,512,768,1024,1088,1536,2048,2560,3072,3584,4096,4608,5120"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "AlphaFold3",
    "what": "single-process JAX/XLA protein structure inference on ROCm (no MPI, no HDF5)",
    "languages": ["Python"],
    "systems": ["tuolumne (ROCm 6.0.0, jaxlib 0.4.34 + jax_rocm60)"],
    "inputs": {
        "model_dir": "AF3's _DEFAULT_MODEL_DIR (MODEL_DIR flag default in run_alphafold.py) already points at <af3-weights-group>/alphafold_data/params_af3/ on Tuolumne: no --model_dir needed once readable; read via the real path, never a workspace symlink",
        "smoke_input": "1eby from <af3-sample-group>/smol_workflow/pdbbind_casf2016_sample/01_af/ (18 MB MSA, smallest available, ~110 s: featurize ~25 s + inference ~85 s over 5 seeds); no smaller fixture exists",
        "msa": "read-only .a3m inputs, read via their real path",
    },
    "env": {
        "LD_LIBRARY_PATH": "Cray CCE runtime libs BEFORE the venv activates (else dftracer's C extension silently falls back to a NoOpProfiler: zero trace)",
    },
    "venv_patch": "jax_triton/__init__.py: REPLACE the stock 'try/except AttributeError: raise ImportError' block guarding gpu_triton.get_compute_capability/get_serialized_metadata with 'get_compute_capability = None' and 'get_serialized_metadata = None' (do not append after it); verify python -c 'import jax_triton' and grep that the try/except is gone",
    "annotate": {
        "decorator_order": "@functools.cache / @functools.lru_cache OUTERMOST, @_dft.log innermost (closest to def)",
        "files_seen": ["data/pipeline.py::_get_protein_msa_and_templates", "model/pipeline/inter_chain_bonds.py"],
    },
    "run": {
        "optimized_buckets": "--buckets=" + TUNED_BUCKETS,
        "default_buckets": DEFAULT_BUCKETS,
        "correctness": "compare <id>_summary_confidences.json ptm/iptm/ranking_score, never a CIF byte-diff",
        "cost_decomposition": "separate seed 1 (XLA compile ~32-43 s + run) from seeds 2+ (steady state) via absl log timestamps",
    },
    "variants": {
        "smoke_1eby": {"input": "1eby", "wall": "~110 s"},
        "large_1e66": {"input": "1e66", "baseline_wall": "1077-1097 s", "tuned_buckets_wall": "793 s (~27% less)"},
    },
    "notes": [
        "steady-state per-seed inference scales as N_bucket^2.02 (padded token count), plus a fixed ~32-43 s XLA JIT compile per process",
        "a bucket must stay a multiple of 64/128: 248 vs 256 at 1eby is a net no-op/regression",
        "XLA_PYTHON_CLIENT_PREALLOCATE=false helps at 1eby scale only; at 1e66 1109 s vs 1077-1097 s (no gain)",
        "--flash_attention_implementation=triton silently falls back to xla on ROCm (needs Ampere+; triton probe nulled)",
        "--jax_compilation_cache_dir: cache hit then RESOURCE_EXHAUSTED HIP_ERROR_OutOfMemory; untested workaround XLA_FLAGS=--xla_gpu_enable_command_buffer=",
        "--xla_gpu_autotune_level changed ranking_score in the 2nd decimal (0.81 -> 0.80)",
        "dftracer installed with DFTRACER_ENABLE_MPI=ON (auto-detected Cray MPICH) does not block FUNCTION-mode tracing",
        "if dftracer-build-smoke lacks session_service_start/stop, use session_run_smoke_test alone and flag the missing node-counter bracketing",
    ],
}

RULES = [
    {"id": "no_cif_diff", "forbid": r"\b(diff|cmp)\b.*_model\.cif",
     "why": "AF3 is run-to-run nondeterministic on GPU: identical baselines differ by thousands of CIF lines",
     "fix": "compare ptm/iptm/ranking_score from <id>_summary_confidences.json"},
    {"id": "no_triton_credit", "forbid": r"--flash_attention_implementation=triton",
     "why": "triton flash attention silently falls back to xla on ROCm (requires Ampere+; the probe is nulled by the ROCm patch)",
     "fix": "keep xla; do not credit a triton flag without proving kernel selection via profiler kernel names"},
    {"id": "compile_cache_crash", "forbid": r"--jax_compilation_cache_dir(?!.*xla_gpu_enable_command_buffer=)",
     "why": "a persistent compilation cache hit crashes run_inference with HIP_ERROR_OutOfMemory (jaxlib 0.4.34, ROCm 6.0.0)",
     "fix": "drop the cache dir, or test XLA_FLAGS=--xla_gpu_enable_command_buffer= first (unverified)"},
    {"id": "decorator_order", "forbid": r"@_dft\.log\s*(\\n|;|\s)+@functools\.(lru_)?cache",
     "why": "'TypeError: unsupported callable' at import: @_dft.log calls inspect.getfullargspec on the lru_cache wrapper",
     "fix": "put @functools.cache / lru_cache outermost and @_dft.log innermost"},
    {"id": "triton_patch_replace", "forbid": r">>\s*\S*jax_triton/__init__\.py",
     "why": "appending the None overrides after the stock try/except ... raise ImportError block is dead code",
     "fix": "replace the try/except block itself with the two None assignments, then re-import and grep"},
    {"id": "cce_libs_before_venv", "require": r"LD_LIBRARY_PATH=.*cce|LD_LIBRARY_PATH=.*cray", "when": r"dftracer|DFTRACER_",
     "why": "without Cray CCE runtime libs on LD_LIBRARY_PATH before the venv activates dftracer silently uses a NoOpProfiler",
     "fix": "export the CCE runtime lib dir on LD_LIBRARY_PATH before activating the venv"},
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
    def workload_af3_recipe(variant: str = "") -> dict:
        """Predictor: the AlphaFold3 recipe dftracer-agents verified - default model dir and smallest input (1eby), the CCE
        LD_LIBRARY_PATH env, the ROCm jax_triton patch, decorator order for annotation, the confirmed 64-aligned bucket list
        (1280 -> 1088, ~27% at 1e66), correctness via ptm/iptm and the known non-wins. variant: '' (all), 'smoke_1eby' or
        'large_1e66'. Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_af3_check(commands: list) -> dict:
        """Validator: check a proposed AF3 recipe, command list or code snippet against the skill's rules (no CIF byte-diff
        correctness, no credit for triton flash attention on ROCm, no compilation cache without the command-buffer workaround,
        cache decorator outermost, jax_triton patch replaced not appended, CCE libs on LD_LIBRARY_PATH when tracing).
        commands: list of lines (or one newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
