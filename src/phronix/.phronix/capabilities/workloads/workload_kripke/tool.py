"""workload_kripke: the Kripke (LLNL deterministic Sn transport proxy app, C++17 + RAJA/Umpire/CHAI, BLT/CMake superbuild)
build, annotation and run recipe that dftracer-agents' workload-kripke skill verified on an MI300A system, as structured
data (predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator).
Nothing here runs a build or a job."""
import json
import re

CAP = "workload_kripke"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "Kripke",
    "what": "discrete-ordinates (Sn) Boltzmann transport (Kobayashi benchmark 3i); ~5k lines of C++ plus RAJA/Umpire/CHAI/BLT submodules",
    "build_system": "cmake (BLT); configure the inner project cmake/kripke, not the ExternalProject superbuild",
    "languages": ["C++17"],
    "systems": ["tuolumne (MI300A)"],
    "submodules": "git submodule update --init --recursive (eight submodules)",
    "configure": [
        "cmake <src>/cmake/kripke -DKRIPKE_SOURCE_ROOT=<src> -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_C_COMPILER=$CC "
        "-DCMAKE_CXX_COMPILER=$CXX -DENABLE_MPI=On -DENABLE_OPENMP=On -DENABLE_TESTS=Off -DENABLE_EXAMPLES=Off "
        "-DBLT_SOURCE_DIR=<src>/blt -DRAJA_ENABLE_EXERCISES=Off -DRAJA_ENABLE_EXAMPLES=Off -DRAJA_ENABLE_TESTS=Off -DRAJA_ENABLE_BENCHMARKS=Off",
    ],
    "build": ["make kripke.exe   # by name, not all"],
    "variants": {
        "cpu": {"flags": "-DENABLE_MPI=On -DENABLE_OPENMP=On", "note": "a few minutes, needs only RAJA (default choice)"},
        "hip": {"flags": "-DENABLE_HIP=On -DENABLE_CHAI=On", "note": "drags in CAMP + Umpire + CHAI for the GPU: larger, fragile; only when GPU kernel tracing is the goal"},
    },
    "annotate": {
        "compile_flags": "-std=c++17 -I<src>/src -I<build>/include -I<src>/tpl/raja/include -I<build>/raja/include "
                         "-I<src>/tpl/raja/tpl/camp/include -I<build>/raja/tpl/camp/include -I<mpi>/include",
        "exclude_dirs": ["/tpl/", "/blt/", "/scripts/", "/host-configs/"],
        "add_back_by_hand": [
            {"fn": "Kripke::Kernel::sweepSubdomain", "file": "Kripke/Kernel/SweepSubdomain.cpp", "comp": "cpu"},
            {"fn": "SweepComm::addSubdomain/workRemaining/readySubdomains/markComplete", "file": "Kripke/ParallelComm/SweepComm.cpp", "comp": "comm"},
            {"fn": "Kripke::Generate::generateEnergy", "file": "Kripke/Generate/*", "comp": "cpu"},
        ],
        "fini_order": "DFTRACER_CPP_REGION_END(main); DFTRACER_CPP_FINI(); Kripke::Core::Comm::finalize();  (+ FINI in usage() before Comm::finalize/exit(1))",
        "never_annotate": ["Kripke/Arch/*.h", "Core/Field.h", "Core/Set.h", "Core/VarLayout.h", "VarTypes.h", "Core/Comm.h"],
        "correctly_skipped": ["Core/BaseVar.cpp", "Core/DataStore.cpp", "Core/MemoryManager.cpp"],
    },
    "run": {
        "decomposition": "--procs x,y,z product = ranks; --zones divisible by it",
        "probe": "--zones 16,16,16 --niter 5 (1 rank, few seconds)",
        "measured": "2 nodes x 4 ranks, 23 cores/rank, OMP_NUM_THREADS=23: --zones 96,96,96 --niter 15 --procs 2,2,2 ~45 s, ~930k events (full annotation + PAPI); wall ~linear in niter",
        "launch": "flux run -N2 -n8 -c23 env OMP_NUM_THREADS=23 <build>/kripke.exe --zones 96,96,96 --niter 15 --procs 2,2,2",
    },
    "verification": [
        "banner: MPI Enabled: Yes, OpenMP Enabled: Yes, Architecture: OpenMP",
        "ldd kripke.exe | grep dftracer shows libdftracer_core.so",
        "DFTRACER_ENABLE=0 run: per-iteration 'particle count=' lines identical to pristine",
        "trace: CPP_APP present AND sweepSubdomain present",
    ],
    "notes": [
        "KRIPKE_ARCH defaults to Sequential and is overridden by ENABLE_OPENMP/CUDA/HIP; the printed banner is authoritative",
        "the SweepSolver polling loop (workRemaining -> readySubdomains -> testRecieves -> MPI_Testany) is ~70% of events at 8 ranks",
        "instrumentation overhead with DFTRACER_ENABLE=0: ~0.6% wall, particle counts bit-identical",
        "Kripke writes no data files: only startup I/O plus stdout",
    ],
}

RULES = [
    {"id": "source_root", "require": r"-DKRIPKE_SOURCE_ROOT=", "when": r"\bcmake\b.*cmake/kripke",
     "why": "the inner CMakeLists FATAL_ERRORs without KRIPKE_SOURCE_ROOT", "fix": "add -DKRIPKE_SOURCE_ROOT=<src>"},
    {"id": "superbuild", "require": r"cmake/kripke", "when": r"\bcmake\b.*-DENABLE_MPI",
     "why": "the top-level CMakeLists is an ExternalProject superbuild that only adds adiak for Caliper and hides the build",
     "fix": "configure <src>/cmake/kripke directly with -DKRIPKE_SOURCE_ROOT and -DBLT_SOURCE_DIR"},
    {"id": "raja_extras_off", "require": r"-DRAJA_ENABLE_EXERCISES=Off", "when": r"\bcmake\b.*-DENABLE_MPI",
     "why": "Kripke's ENABLE_EXAMPLES=Off does not reach RAJA: ~100 RAJA tutorial binaries get built",
     "fix": "add -DRAJA_ENABLE_EXERCISES=Off -DRAJA_ENABLE_EXAMPLES=Off -DRAJA_ENABLE_TESTS=Off -DRAJA_ENABLE_BENCHMARKS=Off"},
    {"id": "submodules", "require": r"git submodule update --init --recursive", "when": r"git clone",
     "why": "'The BLT submodule is not present.' / 'CAMP submodule not initialized'", "fix": "git submodule update --init --recursive"},
    {"id": "no_header_annotation", "forbid": r"clang_annotate_file\(.*(Arch/\w+\.h|Field\.h|Set\.h|VarLayout\.h|VarTypes\.h|Comm\.h)",
     "why": "Kripke headers are RAJA policy typedefs or per-element accessors; Comm.h MPI wrappers are already intercepted",
     "fix": "annotate only the 26 src/*.cpp files"},
    {"id": "compile_flags_given", "require": r"compile_flags", "when": r"clang_annotate_project",
     "why": "without the include flags KripkeConfig.h is not found: functions: 0 with a green status",
     "fix": "pass compile_flags with -I<src>/src -I<build>/include and the RAJA/camp include dirs"},
    {"id": "exclude_tpl", "require": r"/tpl/", "when": r"clang_annotate_project",
     "why": "the annotated tree is ~1900 files with submodules, Kripke's own is 26", "fix": "exclude [/tpl/, /blt/, /scripts/, /host-configs/]"},
    {"id": "procs_given", "require": r"--procs\s+\d+,\d+,\d+", "when": r"kripke\.exe",
     "why": "Kripke decomposes space as --procs x,y,z whose product must equal the rank count", "fix": "pass --procs x,y,z"},
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
    def workload_kripke_recipe(variant: str = "") -> dict:
        """Predictor: the Kripke recipe dftracer-agents verified - submodules, inner cmake/kripke configure with RAJA extras
        off, annotation compile flags, excluded dirs, the functions to add back by hand, FINI-before-Comm::finalize, headers to
        leave alone, run decomposition/sizing and the verification checklist. variant: '' (all), 'cpu' or 'hip'.
        Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_kripke_check(commands: list) -> dict:
        """Validator: check a proposed Kripke recipe or command list against the skill's rules (inner project with
        KRIPKE_SOURCE_ROOT, RAJA extras off, submodules initialised, no header annotation, compile_flags and /tpl/ exclusion
        for the annotator, --procs given). commands: list of shell lines / tool calls (or one newline-separated string / JSON
        text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
