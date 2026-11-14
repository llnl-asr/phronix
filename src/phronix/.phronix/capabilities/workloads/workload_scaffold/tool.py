"""workload_scaffold: the ScaFFold (LBANN PyTorch DDP benchmark, 3D U-Net on procedurally generated fractals) environment,
install, config and run recipe dftracer-agents' workload-scaffold skill verified on Tuolumne MI300A, as structured data
(predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator).
Nothing here installs or runs anything."""
import json
import re

CAP = "workload_scaffold"

RECIPE = {
    "app": "ScaFFold",
    "what": "LBANN PyTorch benchmark: 3D U-Net on procedurally-generated fractals; Python/PyTorch DDP on Tuolumne MI300A",
    "build_system": "pip (one shared venv for app + dftracer + deps)",
    "systems": ["tuolumne"],
    "modules": ["python/3.11.5 (NOT 3.13: the site default breaks dftracer's native ext)", "cce/21.0.0", "cray-mpich/9.1.0",
                "rocm/7.1.1", "rccl/fast-env-slows-mpi"],
    "env": {
        "PIP_INDEX_URL": "https://<wci-index>/simple (a user pip.conf may hide it)", "PIP_TRUSTED_HOST": "<wci-host>",
        "MPI4PY_MPIABI": "mpich",
        "LD_LIBRARY_PATH": "must include <venv>/lib/python3.11/site-packages/torch/lib (else 'RuntimeError: Error in dlopen: libcaffe2_nvrtc.so')",
        "DFTRACER_LOG_FILE": "$WS/<run>/traces/raw/<run>- (session workspace, not Lustre)",
        "LD_PRELOAD": "ROCm LLVM libomp.so (libmagma needs __kmpc_dispatch_deinit) + MKL (libtorch_cpu needs cblas_gemm_f16f16f32)",
    },
    "install": [
        "ml load python/3.11.5", "ml cce/21.0.0 cray-mpich/9.1.0 rocm/7.1.1 rccl/fast-env-slows-mpi",
        "python3 -m venv $WS/venv && source $WS/venv/bin/activate",
        "pip install -e \".[rocmwci]\"   # WCI wheels: torch==2.10.0+rocm710, mpi4py==4.1.1+mpich.9.1.0 (older recipe: pip install \".[rocm]\" --extra-index-url https://download.pytorch.org/whl/rocm7.1)",
        "patchelf torch's MPI SONAME: libmpi_gnu_112.so.12 -> libmpi_gnu.so.12",
        "pip install --pre \"dftracer[modules]\" dftracer-modules && dftracer-compose --enable mpi,hdf5,hip --disable papi,hwloc,cuda",
        "build dftracer with the GNU MPICH wrapper /opt/cray/pe/mpich/9.1.0/ofi/gnu/11.2/bin/mpicc (matches torch/mpi4py and LD_PRELOAD)",
        "export MPI4PY_MPIABI=mpich; mpi4py with the Cray linkage fix (software_mpi)",
        "python -c \"import dftracer; from mpi4py import MPI; import ScaFFold; import torch; print('all OK')\"",
    ],
    "config_overrides": {
        "epochs": "2-5 for bounded runs (default -1 = until dice >= 0.95)", "problem_scale": "7 (128^3; keep realistic)",
        "checkpoint_interval": "1 (default -1 = disabled)", "n_categories": "2-3",
        "dataset_dir": "<lustre>/$USER/workspaces/scaffold/datasets", "fract_base_dir": "<lustre>/$USER/workspaces/scaffold/fractals",
        "base_run_dir": "<lustre>/$USER/workspaces/scaffold/runs", "checkpoint_dir": "same as base_run_dir",
        "smoke": "epochs: 1, problem_scale: 5, n_categories: 1",
        "32_ranks": "n_categories=20, n_instances_used_per_fractal=24 -> 160 volumes -> val 48 / train 112",
        "volumes": "n_categories * n_instances_used_per_fractal / n_fracts_per_vol; train AND val counts must exceed ranks",
        "batch_size": "PER RANK: batch_size * world_size <= training samples",
        "dataloader_num_workers": "4 (top validated fix)",
    },
    "run": {
        "phase_a": "flux run -N 8 -n 32 $WS/venv/bin/scaffold generate_fractals -c <cfg>",
        "phase_b": "torchrun-hpc -N 8 -n 4 --gpus-per-proc 1 $WS/venv/bin/scaffold benchmark -c <cfg>   # datagen_from_scratch: 0",
        "smoke": "torchrun-hpc -N 1 -n 4 --gpus-per-proc 1 $WS/venv/bin/scaffold benchmark -c smoke_config.yml",
        "profiled_4n": "scripts/run_profiled.sh <run_name> <config.yml> (4N x 4GPU, FUNCTION mode, DATA_DIR=all, PROFILE_TORCH + DFTRACER_TORCH_PROFILE, DFTRACER_SERVICE=1 opt-in)",
        "exit_codes": "tolerate 134 only (benign exit-time SIGABRT, libomp + mkl_gnu_thread with gotcha), then validate the trace",
        "queues": "8-node pbatch sits in SCHED; pdebug schedules immediately; check both",
    },
    "variants": {},
    "notes": [
        "generate_fractals.py must NOT call initialize_log() (worker.py inits at import; cli.py imports both): use dftracer.get_instance()",
        "DFTRACER_ENABLE_HIP_TRACING=ON must be exported explicitly when building dftracer; pydftracer installs from its own @develop",
        "dftracer_service cannot run alongside torchrun-hpc (forces --exclusive); dftracer_service start under flux run never returns: use flux submit",
        "checkpoint 256.4 MB per epoch from rank 0; total_train_time excludes it: measure wall clock",
        "ckpt_stage_dir=/dev/shm + shutil.move is +6.3% (REJECT); hardlink_best (temp + os.replace + os.link) -2.5%; best-loss cache -1.9%",
    ],
}

RULES = [
    {"id": "python_311", "forbid": r"\b(?:ml|module)\s+(?:load\s+)?.*\bpython/3\.13",
     "why": "python 3.13 (site default) breaks dftracer's native extension", "fix": "ml load python/3.11.5"},
    {"id": "gnu_mpich_for_dftracer", "forbid": r"mpich/[\d.]+/ofi/crayclang/\S*mpicc",
     "why": "crayclang mpicc links libmpi_cray.so.12 next to the preloaded libmpi_gnu.so.12: 'double free or corruption (!prev)' at exit",
     "fix": "build dftracer with /opt/cray/pe/mpich/9.1.0/ofi/gnu/11.2/bin/mpicc"},
    {"id": "torch_lib_on_ld_path", "require": r"site-packages/torch/lib", "when": r"scaffold\s+benchmark",
     "why": "dftracer's gotcha dlopen interception breaks torch's RPATH lookup: 'RuntimeError: Error in dlopen: libcaffe2_nvrtc.so'",
     "fix": "add <venv>/lib/python3.11/site-packages/torch/lib to LD_LIBRARY_PATH"},
    {"id": "fractals_generated", "require": r"generate_fractals|datagen_from_scratch", "when": r"scaffold\s+benchmark",
     "why": "benchmark cannot synthesize the fractal instances it reads", "fix": "run 'flux run ... scaffold generate_fractals -c <cfg>' first in the same job"},
    {"id": "epochs_override", "forbid": r"\bepochs:\s*-1\b",
     "why": "epochs: -1 trains until dice >= 0.95 (hours)", "fix": "set epochs to a bounded count (2-5, or a fixed budget like 960)"},
    {"id": "checkpoint_override", "forbid": r"\bcheckpoint_interval:\s*-1\b",
     "why": "checkpoint_interval -1 disables checkpoint I/O (nothing to trace)", "fix": "checkpoint_interval: 1"},
    {"id": "no_service_under_flux_run", "forbid": r"flux\s+run\b.*dftracer_service\s+start",
     "why": "dftracer_service start under flux run never returns", "fix": "start it with flux submit"},
    {"id": "no_devshm_stage", "forbid": r"ckpt_stage_dir\s*[=:]\s*/dev/shm",
     "why": "tmpfs and Lustre are different devices: shutil.move becomes read+write, +6.3% (and /dev/shm eats HBM on MI300A)",
     "fix": "drop /dev/shm staging; keep hardlink_best and async_save"},
    {"id": "tolerate_only_134", "forbid": r"\|\|\s*true\b",
     "why": "runner scripts may tolerate exit code 134 only (the known exit-time SIGABRT) and must validate the trace",
     "fix": "check rc in (0, 134) explicitly, then validate the trace"},
]


def _extra(commands):
    text = "\n".join(_commands(commands))
    out = []
    if re.search(r"torchrun-hpc", text) and re.search(r"dftracer_service\s+start", text):
        out.append({"check": "no_service_with_torchrun_hpc", "ok": False,
                    "detail": "torchrun-hpc forces --exclusive on El-Capitan-family systems: a daemon holding 1 core/node makes the job unschedulable",
                    "fix": "do not run dftracer_service alongside torchrun-hpc for ScaFFold"})
    return out


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
    def workload_scaffold_recipe(variant: str = "") -> dict:
        """Predictor: the ScaFFold recipe dftracer-agents verified on Tuolumne MI300A: modules (python/3.11.5, cce 21, cray-mpich
        9.1.0, rocm 7.1.1), one shared venv install with WCI wheels and dftracer on GNU MPICH, env (torch/lib on LD_LIBRARY_PATH,
        LD_PRELOAD), config overrides (epochs, checkpoint_interval, Lustre dirs, volume sizing), the two-phase run
        (generate_fractals then torchrun-hpc benchmark), smoke shape and exit-code policy. variant: optional (none defined).
        Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_scaffold_check(commands: list) -> dict:
        """Validator: check a proposed ScaFFold recipe, config lines or command list against the skill's rules: python 3.11
        not 3.13, GNU (not crayclang) MPICH for dftracer, torch/lib on LD_LIBRARY_PATH, fractals generated before benchmark,
        bounded epochs and checkpoint_interval, no dftracer_service with torchrun-hpc or under flux run, no /dev/shm checkpoint
        staging, only rc 134 tolerated. commands: list of lines (or newline/JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _extra(commands)
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res
