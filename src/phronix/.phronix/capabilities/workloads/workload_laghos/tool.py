"""workload_laghos: the Laghos (CEED/Laghos, MFEM high-order Lagrangian hydrodynamics miniapp, HIP via MFEM) build,
annotation, run, aggregation and PAPI/variorum recipe dftracer-agents' workload-laghos skill verified on Tuolumne MI300A (as
deployed by llnl/ice4hpc_data), as structured data (predictor), and a deterministic check of a proposed recipe or command
list against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_laghos"

PAPI_RUNS = {
    "cache_p1": "PAPI_L1_DCM,PAPI_L2_DCM,PAPI_L2_ICM,PAPI_L2_TCM,PAPI_L2_DCH,PAPI_L1_DCA,PAPI_L2_DCR",
    "cache_p2": "PAPI_L2_ICH,PAPI_L2_ICA,PAPI_L2_ICR,PAPI_L2_TCH",
    "tlb": "PAPI_TLB_DM,PAPI_TLB_IM",
    "branch": "PAPI_BR_UCN,PAPI_BR_CN,PAPI_BR_TKN,PAPI_BR_NTK,PAPI_BR_MSP,PAPI_BR_PRC,PAPI_BR_INS",
    "flop_p1": "PAPI_FMA_INS,PAPI_FP_INS,PAPI_VEC_INS",
    "flop_p2": "PAPI_FML_INS,PAPI_FAD_INS",
    "flop_p3": "PAPI_FDV_INS,PAPI_FSQ_INS",
    "flop_p4": "PAPI_FP_OPS",
    "inscyc": "PAPI_TOT_INS,PAPI_TOT_CYC",
}

RECIPE = {
    "app": "Laghos",
    "repo": "https://github.com/CEED/Laghos (ice4hpc pinned commit a2ad322, 2025-05-09)",
    "what": "time-dependent Euler equations in a moving Lagrangian frame, high-order FEM on MFEM; GPU via MFEM (-d hip); no app file I/O in the solve loop",
    "deployment_ref": "llnl/ice4hpc_data apps_per_machine/tuolumne/laghos/{README.txt,makefile,makefile-serial}",
    "build_system": "make (MFEM config.mk) + explicit README link",
    "systems": ["tuolumne"],
    "modules": ["rocm/6.4.2", "rocmcc/6.4.2-cce-20.0.0-magic (auto-replaces cce/20.0.0)", "cray-mpich/9.0.1", "cmake/3.29.2"],
    "env": {"CC": "<cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic>/bin/mpiamdclang",
            "CXX": "<cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic>/bin/mpiamdclang++",
            "ICE4HPC_PREFIX": "<group-readable prefix with MFEM 4.8.1 / Hypre / METIS 5.1.0 / Umpire>"},
    "source_prep": ["dos2unix laghos.cpp", "LC_ALL=C tr -cd '\\0-\\177' < laghos.cpp > tmp && mv tmp laghos.cpp",
                    "flatten MFEM config.mk/test.mk generator expressions and the bare dl with the README's two sed lines"],
    "build": ["set +e; make  # EXPECTED to fail at link: sticky -x hip makes clang read laghos.o as HIP source", "set -e",
              "ls *.o   # objects must exist", "<explicit link command from the ice4hpc README>"],
    "dftracer_install": "session_install_dftracer(..., hdf5=False, hip=True, rocm_path='/opt/rocm-6.4.2')",
    "annotation": {
        "compile_flags": "-std=c++17 -D__HIP_PLATFORM_AMD__=1 -DUSE_PROF_API=1 -DCAMP_HAVE_HIP -DFMT_HEADER_ONLY=1 "
                         "-I$ICE4HPC_PREFIX/include -I$ICE4HPC_PREFIX/include/mfem -I$ROCM_PATH/include -I$ROCM_PATH/include/rocrand "
                         "-I<cray-mpich ...-rocmcc-...>/include -I<session venv>/lib/python3.13/site-packages/dftracer/include",
        "derive": "MFEM_INCFLAGS + makefile EXTRA_INC_DIR (include/mfem) + MPI wrapper include; strip -x hip and --offload-arch=",
        "expected": "15/22 solver functions, 5/11 assembly functions",
        "add_by_hand": ["LagrangianHydroOperator::Mult", "AssembleForceMatrix (RAII guard: early return needs no END)"],
        "fini": "DFTRACER_CPP_FINI() (with REGION_END) on EVERY one of main's five exits (return 1 x2, return 3 x2, return 0), before MPI_Finalize()",
        "verify": "grep -n \"DFTRACER_CPP_REGION_START\\|DFTRACER_CPP_REGION_END\\|DFTRACER_CPP_FINI\" laghos.cpp",
    },
    "run": {
        "layout": "4 ranks per node, -g1 per rank (-c23 at 4 nodes)",
        "smoke": "-p 0 -dim 3 -rs 1 -tf 0.05 (seconds)",
        "baseline_1n": "flux run -N 1 -n 4 -g1 ./laghos -p 1 -dim 3 -rs 2 -tf 0.6 -pa -d hip --no-visualization (~370 s, 560 steps, Energy diff 6.90e-06)",
        "baseline_4n": "flux run -N 4 -n 16 -g1 -c23 ./laghos -p 1 -dim 3 -rs 3 -tf 0.15 -pa -d hip (343 s, 628 steps, Energy diff 6.90e-06)",
        "check_device": "laghos prints 'Device configuration: hip,cpu'",
        "sizing": "untraced rs=3 / 16 ranks: tf=0.03 -> 335 steps in 101 s, scale linearly; rs=3 ~3x the steps of rs=2",
    },
    "aggregation": {"env": {"DFTRACER_ENABLE_AGGREGATION": "1", "DFTRACER_AGGREGATION_TYPE": "SELECTIVE (uppercase, case-sensitive)",
                            "DFTRACER_AGGREGATION_FILE": "<ws>/scripts/aggregation.yaml"},
                    "yaml": "inclusion: [\"dur < 100\"]",
                    "fields": ["cat", "name", "ts", "dur", "app", "rank", "tags.<name>"],
                    "size_first": "dur < 1000 cut 165,710 -> 10,726 events but drops per-event GPU/MPI detail"},
    "papi_exact_runs": PAPI_RUNS,
    "papi_env": {"DFTRACER_PAPI_EVENTS": "<one run's comma list>", "DFTRACER_PAPI_MULTIPLEX": "0"},
    "variorum_build": {"DFTRACER_ENABLE_VARIORUM": "ON", "DFTRACER_BUILD_VARIORUM": "ALWAYS"},
    "split": "dftracer_split <dir> --output <out> --chunk-size <MB>   (app + service traces in one dir; prefix service_<host> per run when combining)",
    "variants": {},
    "notes": [
        "Laghos does not need HDF5: pass hdf5=False to session_install_dftracer",
        "session_detect reports hip: false (GPU only through MFEM_FORALL): pass hip=True and rocm_path=/opt/rocm-6.4.2",
        "PAPI family-grouped layout: 5.04x fewer records but only ~9% smaller on disk; single lowercase 'papi' cat",
        "service_*.pfw.gz sizes are not comparable unless each run had a clean single daemon lifecycle",
    ],
}

RULES = [
    {"id": "prebuilt_toolchain", "forbid": r"\bmodule\s+load\s+(?:PrgEnv-cray|cce/)",
     "why": "the prebuilt MFEM/Hypre/METIS/Umpire were built with cray-mpich-9.0.1-rocmcc-6.4.2-cce-20.0.0-magic; the site default mixes libstdc++/ROCm ABIs",
     "fix": "module load rocm/6.4.2 rocmcc/6.4.2-cce-20.0.0-magic cray-mpich/9.0.1 cmake/3.29.2"},
    {"id": "rocmcc_module", "require": r"rocmcc/6\.4\.2-cce-20\.0\.0-magic", "when": r"\bmodule\s+load\b",
     "why": "the session must use the compilers the prebuilt dependencies were built with", "fix": "module load rocmcc/6.4.2-cce-20.0.0-magic"},
    {"id": "source_prep", "require": r"dos2unix", "when": r"(^|[;&|]\s*)make\b",
     "why": "laghos.cpp ships CRLF + non-ASCII bytes the clang frontend rejects", "fix": "dos2unix laghos.cpp and strip non-ASCII with tr -cd"},
    {"id": "explicit_link_fallback", "require": r"set\s+\+e", "when": r"(^|[;&|]\s*)make\b",
     "why": "the makefile link rule is EXPECTED to fail (sticky -x hip); with set -e / pipefail the script aborts before the fallback link",
     "fix": "set +e around make, check the .o files, then link with the README's explicit command"},
    {"id": "gpu_device", "require": r"-d\s+hip", "when": r"laghos\b.*-p\s+\d",
     "why": "without -d hip Laghos runs on the CPU", "fix": "add -d hip (confirm 'Device configuration: hip,cpu')"},
    {"id": "aggregation_type_upper", "forbid": r"DFTRACER_AGGREGATION_TYPE=(?![\"']?SELECTIVE\b)\S+",
     "why": "compared case-sensitively against SELECTIVE; anything else silently falls back to FULL (all per-event detail lost)",
     "fix": "DFTRACER_AGGREGATION_TYPE=SELECTIVE"},
    {"id": "aggregation_on", "require": r"DFTRACER_ENABLE_AGGREGATION=1", "when": r"laghos\b.*-d\s+hip",
     "why": "with HIP tracing on an unaggregated run is enormous (10.96 M events, ~30 MB/rank on 4 ranks)",
     "fix": "export DFTRACER_ENABLE_AGGREGATION=1 DFTRACER_AGGREGATION_TYPE=SELECTIVE with inclusion [\"dur < 100\"]"},
    {"id": "dur_100_not_1000", "forbid": r"dur\s*<\s*1000\b",
     "why": "dur < 1000 is size-first: nearly every GPU dispatch and MPI op is sub-threshold, so per-event detail is lost",
     "fix": "use dur < 100 unless total corpus size is the binding constraint"},
    {"id": "split_flags", "forbid": r"dftracer_split\b.*(--output-dir|--chunk-size-mb)",
     "why": "these flags do not exist: the tool prints usage and exits 0 (looks like a successful no-op)", "fix": "use --output and --chunk-size (MB)"},
    {"id": "no_hdf5", "require": r"hdf5\s*=\s*False", "when": r"session_install_dftracer",
     "why": "Laghos does no HDF5 I/O; detection auto-enables a system HDF5 anyway", "fix": "pass hdf5=False"},
    {"id": "hip_explicit", "require": r"hip\s*=\s*True", "when": r"session_install_dftracer",
     "why": "session_detect finds no HIP in the app source (it reaches the GPU via MFEM_FORALL)", "fix": "pass hip=True"},
    {"id": "rocm_path_pinned", "require": r"rocm-6\.4\.2", "when": r"session_install_dftracer",
     "why": "detection picks the newest ROCm module, which does not match the app's", "fix": "pass rocm_path=/opt/rocm-6.4.2"},
    {"id": "papi_no_multiplex", "require": r"DFTRACER_PAPI_MULTIPLEX=0", "when": r"DFTRACER_PAPI_EVENTS=",
     "why": "5 hardware registers: an over-full list multiplexes into estimates", "fix": "set DFTRACER_PAPI_MULTIPLEX=0 and use a verified subset (papi_exact_runs)"},
    {"id": "variorum_always", "require": r"DFTRACER_BUILD_VARIORUM=ALWAYS", "when": r"DFTRACER_ENABLE_VARIORUM=ON",
     "why": "a distribution variorum on MI300A reports _ERROR_VARIORUM_UNSUPPORTED_PLATFORM and yields no power", "fix": "-DDFTRACER_BUILD_VARIORUM=ALWAYS"},
    {"id": "annotate_flags_clean", "forbid": r"clang_(?:annotate|extract)\w*.*(?:-x\s+hip|--offload-arch)",
     "why": "MFEM_INCFLAGS' -x hip / --offload-arch= break the extractor", "fix": "strip -x hip and --offload-arch= from the compile flags"},
    {"id": "annotate_include_paths", "require": r"include/mfem", "when": r"clang_(?:annotate|extract)",
     "why": "without include paths general/forall.hpp is fatal, the AST is empty and 0 of 15 solver functions annotate (status still ok)",
     "fix": "pass compile_flags with -I$ICE4HPC_PREFIX/include and -I$ICE4HPC_PREFIX/include/mfem (+ ROCm, MPI, dftracer include)"},
]


def _extra(commands):
    """Every PAPI subset must be one of the verified exact runs (subsets are probed, not derived by counting names)."""
    out = []
    known = {",".join(sorted(v.split(","))) for v in PAPI_RUNS.values()}
    for c in _commands(commands):
        m = re.search(r"DFTRACER_PAPI_EVENTS=[\"']?([A-Z0-9_,]+)", c)
        if not m:
            continue
        key = ",".join(sorted(x for x in m.group(1).split(",") if x))
        ok = key in known
        out.append({"check": "papi_subset_verified", "ok": ok,
                    "detail": "ok" if ok else f"{m.group(1)} is not one of the 9 probed exact runs (FLOP fits only 3 of 8, CACHE 7 of 11)",
                    "fix": "" if ok else "use a papi_exact_runs subset from workload_laghos_recipe, or probe PAPI_start/PAPI_stop and pack greedily"})
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
    def workload_laghos_recipe(variant: str = "") -> dict:
        """Predictor: the Laghos recipe dftracer-agents verified on Tuolumne MI300A: the rocmcc/cray-mpich toolchain pinned by the
        prebuilt MFEM deps, source prep and the expected make link failure + explicit link, session_install_dftracer flags
        (hdf5=False, hip=True, rocm 6.4.2), annotation compile flags and FINI-on-every-exit, run configs and sizing, SELECTIVE
        aggregation (dur < 100), the 9 exact PAPI runs, variorum build flags and dftracer_split flags. variant: optional (none
        defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_laghos_check(commands: list) -> dict:
        """Validator: check a proposed Laghos recipe or command list against the skill's rules: rocmcc toolchain (no PrgEnv-cray /
        cce), dos2unix + set +e around make, -d hip, aggregation on with uppercase SELECTIVE and dur < 100, dftracer_split
        --output/--chunk-size, hdf5=False/hip=True/rocm-6.4.2 on install, PAPI multiplex 0 with a verified subset, variorum
        ALWAYS, annotation flags with include/mfem and without -x hip. commands: list of shell lines (or newline/JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _extra(commands)
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res
