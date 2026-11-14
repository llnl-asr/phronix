"""workload_minivite: the miniVite (ECP-ExaGraph distributed Louvain community-detection proxy, C++11, MPI+OpenMP, plain
Makefile) build, annotation and run recipe that dftracer-agents' workload-minivite skill verified on an MI300A/Cray system,
as structured data (predictor), and a deterministic check of a proposed recipe or command list against that skill's rules
(validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_minivite"

HOT = ["distExecuteLouvainIteration", "distGetMaxIndex", "distBuildLocalMapCounter"]

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "miniVite",
    "repo": "ECP-ExaGraph/miniVite",
    "what": "one phase of the Louvain method for graph community detection in distributed memory",
    "build_system": "make (plain Makefile, CXX = CC by default)",
    "languages": ["C++11"],
    "systems": ["tuolumne (MI300A/Cray)"],
    "layout": {"main.cpp": "main() + parseCommandLine() only", "dspl.hpp": "the distributed Louvain solver (~16 free functions)",
               "graph.hpp": "Graph, BinaryEdgeList (file input), GenerateRGG (synthetic input)",
               "utils.hpp": "LCG random generator, parallel prefix op, small helpers"},
    "build": [
        'make -j 8 CXX="$CXX" CXXFLAGS="-std=c++11 -g -O3 -fopenmp -DPRINT_DIST_STATS -I$DFT/include" '
        'OPTFLAGS="-O3 -fopenmp -DPRINT_DIST_STATS -L$DFT/lib64 -ldftracer_core -Wl,-rpath,$DFT/lib64"',
    ],
    "annotate": {
        "files": ["main.cpp", "dspl.hpp", "graph.hpp", "utils.hpp"],
        "headers_call": "clang_annotate_file(language=\"cpp\", is_entry=False) for each .hpp (clang_annotate_project only finds main.cpp)",
        "compile_flags": "-std=c++11 -fopenmp -DPRINT_DIST_STATS -I<mpi include dir> -include mpi.h",
        "exclude_functions": HOT,
        "expected_functions": ["main (REGION)", "parseCommandLine", "GenerateRGG", "Graph", "generate", "set_nedges", "print_dist_stats",
                               "distSumVertexDegree", "distCalcConstantForSecondTerm", "distInitLouvain", "distComputeModularity",
                               "fillRemoteCommunities", "updateRemoteCommunities", "exchangeVertexReqs", "createCommunityMPIType",
                               "destroyCommunityMPIType", "distLouvainMethod"],
    },
    "run": {
        "options": {"-n <vertices>": "synthetic RGG in memory (no input file)", "-f <bin-file>": "real graph, Vite binary format",
                    "-l": "distributed LCG RNG", "-p <pct>": "random long-range edges", "-t <threshold>": "modularity convergence threshold"},
        "constraints": ["with -n: process count is a power of 2", "with -n: vertices divisible by process count"],
        "env": {"MPICH_MAX_THREAD_SAFETY": "multiple (or build with -DDISABLE_THREAD_MULTIPLE_CHECK)",
                "DFTRACER_PAPI_EVENTS": "PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS"},
        "launch": "flux run -N2 -n16 -c11 env OMP_NUM_THREADS=11 MPICH_MAX_THREAD_SAFETY=multiple ./miniVite -n 2097152",
        "sizing_16_ranks": [{"n": 262144, "wall": "2.2 s"}, {"n": 1048576, "wall": "17.7 s"}, {"n": 2097152, "wall": "73 s (63.1 s RGG gen, 0.18 s Louvain)"},
                            {"n": 4194304, "wall": "> 10 min (killed)"}],
    },
    "variants": {},
    "notes": [
        "RGG generation is O((nv/p)^2): an -n run is a graph-generator benchmark; for Louvain use -f or more ranks",
        "correctness: Modularity and #Iterations identical across pristine / DFTRACER_ENABLE=0 / traced (0.75311, 20 iters)",
        "do not compare 'Average total time' (Louvain phase only, ~0.2-0.35 s, below noise)",
        "PAPI and variorum need the czgitlab dftracer: verify DFTRACER_PAPI_TRACING_ENABLE 1 and DFTRACER_VARIORUM_ENABLE 1 in dftracer_config.hpp",
        "cat 'gpu' type-13 records are variorum node power, not GPU kernels (CPU-only app, dftracer hip=False)",
    ],
}

RULES = [
    {"id": "exclude_hot_helpers", "require": r"distExecuteLouvainIteration.*distGetMaxIndex.*distBuildLocalMapCounter|"
                                             r"(?=.*distExecuteLouvainIteration)(?=.*distGetMaxIndex)(?=.*distBuildLocalMapCounter)",
     "when": r"clang_annotate_(file|project)",
     "why": "per-vertex hot helpers emit O(nv x iters) events per rank from every OpenMP thread",
     "fix": "exclude_functions='[\"distExecuteLouvainIteration\",\"distGetMaxIndex\",\"distBuildLocalMapCounter\"]'"},
    {"id": "annotate_headers", "require": r"dspl\.hpp", "when": r"clang_annotate_(file|project)",
     "why": "clang_annotate_project finds only main.cpp: the solver in dspl.hpp/graph.hpp/utils.hpp stays un-instrumented",
     "fix": "clang_annotate_file(language=\"cpp\", is_entry=False) on dspl.hpp, graph.hpp and utils.hpp"},
    {"id": "force_include_mpi", "require": r"-include\s+mpi\.h", "when": r"clang_annotate_(file|project)",
     "why": "dspl.hpp and utils.hpp use MPI_Datatype/MPI_INT64_T without including <mpi.h>: clang loses functions silently",
     "fix": "add -include mpi.h (and -std=c++11 -fopenmp -DPRINT_DIST_STATS -I<mpi include>) to compile_flags"},
    {"id": "lib_name", "forbid": r"-ldftracer(?!_)",
     "why": "the library is -ldftracer_core; -ldftracer does not exist", "fix": "use -ldftracer_core"},
    {"id": "link_in_optflags", "forbid": r"LDFLAGS=.*dftracer",
     "why": "the Makefile link rule is $(CXX) $^ $(OPTFLAGS) -o $@: LDFLAGS is ignored", "fix": "put the dftracer link flags in OPTFLAGS"},
    {"id": "optflags_overridden", "require": r"OPTFLAGS=", "when": r"\bmake\b.*CXXFLAGS=",
     "why": "CXXFLAGS in the Makefile expands $(OPTFLAGS): override both on the command line", "fix": "pass OPTFLAGS too"},
    {"id": "thread_multiple", "require": r"MPICH_MAX_THREAD_SAFETY=multiple|DISABLE_THREAD_MULTIPLE_CHECK", "when": r"(flux run|srun|mpirun|mpiexec).*miniVite",
     "why": "MPI_Init_thread fails the MPI_THREAD_MULTIPLE check when omp_get_max_threads() > 1 and the app calls MPI_Abort",
     "fix": "export MPICH_MAX_THREAD_SAFETY=multiple or build with -DDISABLE_THREAD_MULTIPLE_CHECK"},
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
    def workload_minivite_recipe(variant: str = "") -> dict:
        """Predictor: the miniVite recipe dftracer-agents verified - make line with dftracer in OPTFLAGS, header annotation
        with -include mpi.h, the three hot helpers to exclude, the 17 expected functions, run options/constraints, RGG sizing
        and the 2-node launch. variant: optional (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_minivite_check(commands: list) -> dict:
        """Validator: check a proposed miniVite recipe or command list against the skill's rules (hot helpers excluded,
        headers annotated, -include mpi.h, -ldftracer_core in OPTFLAGS not LDFLAGS, OPTFLAGS overridden with CXXFLAGS,
        MPICH_MAX_THREAD_SAFETY=multiple). commands: list of shell lines / tool calls (or one newline-separated string /
        JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
