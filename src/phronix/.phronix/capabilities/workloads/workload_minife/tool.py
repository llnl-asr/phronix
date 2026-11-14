"""workload_minife: the miniFE (Mantevo unstructured implicit FE proxy app) build/annotate/run recipe that dftracer-agents'
workload-minife skill verified (Tuolumne openmp45-opt GPU offload, NVIDIA cuda variant), as structured data (predictor),
and a deterministic check of a proposed recipe or command list against that skill's rules (validator). Nothing here runs."""
import json
import re

CAP = "workload_minife"

RECIPE = {
    "app": "miniFE",
    "what": "Mantevo unstructured implicit finite-element proxy app: box mesh, CSR matrix assembly, CG solve (~8k lines); "
            "exercises FE assembly, sparse matvec, MPI halo exchange and collectives",
    "upstream": "github.com/Mantevo/miniFE",
    "pinned_commit": "abe3288 (ice4hpc Tuolumne recipe: llnl/ice4hpc_data apps_per_machine/tuolumne/miniFE/README.txt)",
    "build_system": "make",
    "systems": ["tuolumne", "nvidia-h100 (cuda variant)"],
    "variants": {
        "ref": {"what": "serial/MPI reference", "gpu": False},
        "openmp": {"what": "OpenMP CPU threading", "gpu": False},
        "openmp-opt": {"what": "OpenMP CPU threading (tuned)", "gpu": False},
        "openmp45": {"what": "OpenMP 4.5 target offload", "gpu": True},
        "openmp45-opt": {
            "what": "tuned OpenMP 4.5 target-offload variant: use for any HIP/GPU tracing work on Tuolumne (MI300A gfx942)",
            "gpu": True,
            "modules": ["rocm/6.4.2", "rocmcc/6.4.2-cce-20.0.0-magic", "cray-mpich/9.0.1", "papi/7.2.0.2 (LAST, on its own line)"],
            "env": {"CC": ".../cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic/bin/mpiamdclang",
                    "CXX": ".../cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic/bin/mpiamdclang++"},
            "setup": ["cp <ice4hpc>/Makefile-openmp45-opt openmp45-opt/src/Makefile",
                      "cd openmp45-opt && ln -sfn ../openmp45/basic basic && ln -sfn ../openmp45/fem fem && ln -sfn ../openmp45/utils utils",
                      "git checkout -- openmp45-opt/src/miniFE_info.hpp  # before any annotation pass (make clean deletes it)"],
            "build": ["cd openmp45-opt/src && make"],
            "session_install_dftracer": "hip=True (session_detect reports hip:false: false negative, offload via OpenMP target runtime)",
            "expected_hip_kinds": ["KERNEL_DISPATCH", "MEMORY_COPY", "PAGE_MIGRATION"],
            "empty_hip_kinds_ok": ["HIP_RUNTIME_API", "SCRATCH_MEMORY"],
        },
        "cuda": {
            "what": "NVIDIA GPU variant (old code; three build/run traps)",
            "gpu": True,
            "source_fix": "src/CudaELLMatrix.hpp: #include <nvToolsExt.h> -> #include <nvtx3/nvToolsExt.h> (keep the NVTX calls)",
            "makefile": [
                "CUDA_HOME ?= <cuda-12 root>",
                "NVCC = nvcc -ccbin mpicxx -Xcompiler -fopenmp",
                "NVCCFLAGS = -lineinfo -gencode=arch=compute_90,code=\\\"sm_90,compute_90\\\"",
                "LIBS = -lnvToolsExt -L$(CUDA_HOME)/lib64 -Xlinker -rpath -Xlinker $(CUDA_HOME)/lib64 "
                "-L$(DFTRACER_DIR)/lib64 -ldftracer_core -Xlinker -rpath -Xlinker $(DFTRACER_DIR)/lib64",
            ],
            "run": "srun --gres=gpu:4 --kill-on-bad-exit=1 timeout <s> ./miniFE.x nx=<n> num_devices=<gpus per node>",
            "annotate": "clang -x cuda --cuda-host-only --cuda-path=<root> -I<root>/include parses but returns 0 functions "
                        "(templates): use the anchor-driven header annotator; main.cu: DFTRACER_CPP_INIT after initialize_mpi, "
                        "DFTRACER_CPP_FINI before CudaManager::finalize() and finalize_mpi()",
        },
    },
    "annotate": {
        "macros": "DFTRACER_CPP_FUNCTION() + DFTRACER_CPP_FUNCTION_UPDATE(\"comp\", ...)",
        "files": "openmp45-opt/src/* plus openmp45/utils/*.cpp (vpath %.cpp ../utils)",
        "functions": {
            "src/main.cpp": {"main": "REGION_START/END + INIT/FINI", "add_*_to_yaml": "cpu"},
            "src/driver.hpp": {"driver": "cpu"},
            "src/cg_solve.hpp": {"cg_solve": "cpu"},
            "src/exchange_externals.hpp": {"exchange_externals": "comm", "begin_*": "comm", "finish_*": "comm"},
            "src/make_local_matrix.hpp": {"make_local_matrix": "comm"},
            "src/generate_matrix_structure.hpp": {"generate_matrix_structure": "cpu"},
            "src/assemble_FE_data.hpp": {"assemble_FE_data": "cpu"},
            "src/perform_element_loop.hpp": {"perform_element_loop": "cpu"},
            "src/SparseMatrix_functions.hpp": {"matvec_std::operator()": "gpu", "matvec_overlap::operator()": "gpu",
                                               "matvec": "cpu", "impose_dirichlet": "cpu", "init_matrix": "mem",
                                               "rearrange_matrix_local_external": "mem", "write_matrix": "io"},
            "src/Vector_functions.hpp": {"waxpby": "cpu", "daxpby": "cpu", "dot": "cpu", "dot_r2": "cpu", "write_vector": "io"},
            "utils/BoxPartition.cpp": {"box_partition": "cpu"},
            "src/YAML_Doc.cpp": {"YAML_Doc::generateYAML": "io"},
        },
        "never_annotate": ["fem/Hex8.hpp", "fem/matrix_algebra_3x3.hpp", "fem/gauss_pts.hpp", "sum_into_row", "sum_in_elem_matrix",
                           "sum_in_symm_elem_matrix", "sum_into_global_linear_system", "sum_into_vector", "mytimer"],
        "main_exits": "two exits (return 1 on zero equations, return return_code), each preceded by miniFE::finalize_mpi(): "
                      "REGION_END + FINI before both wrappers",
    },
    "run": ["miniFE.x nx=768 ny=768 nz=768", "omit verify_solution=1 for benchmark runs (fails at every benchmark size: max_iters=200)"],
    "sizing": {"nx=64, 1 rank": "0.35 s CG / 0.86 s total", "nx=256, 4N x 4R": "~17 s", "nx=768, 4N x 4R": "~3 m 45 s, ~9 GB/rank CSR",
               "rule": "max_iters fixed at 200: wall time scales as N^3 / ranks"},
    "env": {"DFTRACER_ENABLE_PAPI_TRACING": "0 for a clean 16/16 (PAPI teardown segfaults 1-3 of 16 ranks), else accept losing a few ranks"},
    "baseline": {"config": "Tuolumne 4 nodes x 4 ranks nx=ny=nz=768", "events": 1165631,
                 "by_source": {"PAPI": 738930, "MPI": 83557, "HIP": 32553, "CPP_APP": 18789, "POSIX/STDIO": 53074,
                               "dftracer_service": 233310}},
    "verify": ["count zero-byte *-app trace files (each = a rank that died before flushing)",
               "event_count is approximate (~): a 10-event raw vs split gap is estimation, not loss",
               "stats --report summary/categories returns 0: compare raw vs split per category instead"],
}

RULES = [
    {"id": "hip_override", "forbid": r"session_install_dftracer\(.*hip\s*=\s*False",
     "why": "openmp45/openmp45-opt reach the GPU through OpenMP target offload; session_detect's hip:false is a false negative",
     "fix": "pass hip=True to session_install_dftracer for the openmp45* variants"},
    {"id": "support_symlinks", "require": r"ln\s+-sfn\s+\.\./openmp45/(?:basic|fem|utils)", "when": r"openmp45-opt",
     "why": "openmp45-opt ships only src/ and builds against openmp45's basic/fem/utils",
     "fix": "ln -sfn ../openmp45/{basic,fem,utils} inside openmp45-opt before the first build"},
    {"id": "restore_info_hpp", "require": r"git\s+checkout\s+--\s+\S*miniFE_info\.hpp", "when": r"make\s+clean",
     "why": "make clean deletes the checked-in miniFE_info.hpp ('fatal error: miniFE_info.hpp file not found' in annotation)",
     "fix": "git checkout -- openmp45-opt/src/miniFE_info.hpp before any annotation pass"},
    {"id": "no_verify_solution", "forbid": r"miniFE\.x\b.*verify_solution=1",
     "why": "verify_solution=1 fails at every benchmark size (max_iters=200, tolerance 0.06): main returns 1 even un-annotated",
     "fix": "omit verify_solution for benchmark runs; A/B against the pristine binary before blaming instrumentation"},
    {"id": "cuda_num_devices", "require": r"num_devices=\d+", "when": r"miniFE\.x.*(?:--gres=gpu|--gpus)|(?:--gres=gpu|--gpus).*miniFE\.x",
     "why": "cuda variant num_devices defaults to 2 and cudaGetDeviceCount is never called: invalid device ordinal or 2 ranks per GPU",
     "fix": "pass num_devices=<gpus per node> with --gres=gpu:4"},
    {"id": "cuda_no_gpus_per_task", "forbid": r"--gpus-per-task=1.*miniFE|miniFE.*--gpus-per-task=1",
     "why": "--gpus-per-task=1: rank 1 computes 1 % 2 = 1 -> cudaErrorInvalidDevice, rank 0 hangs in the next collective",
     "fix": "--gres=gpu:4 + num_devices=4, plus --kill-on-bad-exit=1 and an outer timeout"},
    {"id": "nvcc_rpath", "forbid": r"nvcc.*-Wl,-rpath",
     "why": "nvcc rejects -Wl,-rpath,X ('Unknown option') and -Xcompiler splits it on commas ('unrecognized option -Wl')",
     "fix": "use -Xlinker -rpath -Xlinker <dir>"},
    {"id": "keep_nvtx_calls", "forbid": r"(?:sed|grep -v).*nvtxRange",
     "why": "do not delete the NVTX calls: they surface as CUDA_MARKER events under CUPTI",
     "fix": "only change the include to <nvtx3/nvToolsExt.h>"},
    {"id": "no_sm35", "forbid": r"sm_35|compute_35", "why": "the stock Makefile's sm_35 is not accepted by CUDA 12",
     "fix": "-gencode=arch=compute_90,code=\"sm_90,compute_90\" (H100)"},
    {"id": "papi_last", "forbid": r"module\s+load\s+.*papi\S*\s+\S+",
     "why": "papi must be loaded LAST, on its own line (system_tuolumne)",
     "fix": "module load papi/7.2.0.2 alone, after rocm/rocmcc/cray-mpich"},
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
    def workload_minife_recipe(variant: str = "") -> dict:
        """Predictor: the miniFE recipe dftracer-agents verified: five variants (ref, openmp, openmp-opt, openmp45, openmp45-opt)
        plus cuda, Tuolumne openmp45-opt modules/CC/symlinks, the annotation table and never-annotate list, run CLI, sizing,
        known-good baseline and trace-verification gotchas. variant: optional (e.g. "openmp45-opt", "cuda") to return only
        that variant. Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_minife_check(commands: list) -> dict:
        """Validator: check a proposed miniFE command list against the skill's rules (hip=True override, openmp45 symlinks,
        restore miniFE_info.hpp after make clean, no verify_solution=1, cuda num_devices / no --gpus-per-task=1, nvcc
        -Xlinker rpath, keep NVTX calls, no sm_35, papi module last). commands: list of shell lines (or a newline-separated
        string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
