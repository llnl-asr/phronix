"""workload_amg2023: the AMG2023 (LLNL/AMG2023, thin C driver over hypre) CPU MPI+OpenMP build, annotation and run recipe
dftracer-agents' workload-amg2023 skill verified on Tuolumne, as structured data (predictor), and a deterministic check of a
proposed recipe or command list against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_amg2023"

RECIPE = {
    "app": "AMG2023",
    "repo": "LLNL/AMG2023 (LLNL-CODE-846758)",
    "what": "parallel algebraic-multigrid benchmark; one 3079-line C file amg.c over libHYPRE",
    "build_system": "cmake (do NOT use the hand-edited Makefile: HYPRE_DIR hardcoded to a home dir, links CUDA/Umpire unconditionally)",
    "systems": ["tuolumne"],
    "dependencies": {
        "hypre": [
            "git clone --depth 1 --branch v2.32.0 https://github.com/hypre-space/hypre.git $WS/hypre-src",
            "cd $WS/hypre-src/src",
            "./configure --prefix=$WS/hypre --with-MPI --with-openmp --enable-shared CC=\"$CC\" CXX=\"$CXX\"",
            "make -j 8 && make install",
            "grep -E 'HYPRE_USING_(OPENMP|HIP|CUDA)|HYPRE_SEQUENTIAL|HYPRE_RELEASE_VERSION' $WS/hypre/include/HYPRE_config.h"
            "   # want HYPRE_USING_OPENMP 1, HYPRE_SEQUENTIAL undef, HYPRE_USING_HIP/CUDA undef",
        ],
        "hypre_min_version": "2.27.0 (built in the session workspace; never a system/Cray hypre)",
    },
    "configure": [
        "cmake -S $WS/source -B $WS/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=\"$CC\" -DCMAKE_CXX_COMPILER=\"$CXX\" "
        "-DHYPRE_PREFIX=\"$WS/hypre\" -DAMG_WITH_MPI=TRUE -DAMG_WITH_OMP=TRUE",
    ],
    "build": ["cmake --build $WS/build -j"],
    "build_notes": [
        "CMakeLists.txt refuses an in-source build: configure out-of-source",
        "LINKER_LANGUAGE CXX although pure C: the link runs through mpic++",
        "AMG_WITH_OMP=TRUE -> -openmp under Cray CCE, pulls libcraymp.so (expected)",
        "session_patch_build links -ldftracer, which does not exist: patch target_link_libraries to -ldftracer_core",
    ],
    "annotation": {
        "functions": {"main": "yes", "BuildIJLaplacian27pt": "yes", "BuildIJLaplacian7pt": "yes (only other problem ids)",
                      "hypre_map27": "no (6-line index mapper in the innermost assembly loop)"},
        "expected": "3 annotated, 1 cost-filtered; at run time -problem 1 gives 2 C_APP events per rank",
        "do_not_annotate": "hypre (~800 C files, O(10^9) kernel calls per solve); brahma interception already captures its MPI/POSIX/STDIO",
        "main_layout": ["hypre_MPI_Init(&argc, &argv);", "DFTRACER_C_INIT(NULL, NULL, NULL);", "DFTRACER_C_FUNCTION_START();",
                        "DFTRACER_C_FUNCTION_UPDATE_STR(\"comp\", \"cpu\");", "...", "DFTRACER_C_FUNCTION_END();", "DFTRACER_C_FINI();",
                        "hypre_MPI_Finalize();", "return (0);"],
        "exits": "main has five exit paths (usage exit(1), two return(-1) precond checks, return(0)) needing END+FINI; both "
                 "BuildIJLaplacian* carry their own exit(1) topology check that needs FINI",
    },
    "run": {
        "args": "-P p q r (p*q*r == ranks) -n nx ny nz (grid PER RANK, weak scaling) -problem 1",
        "sizing_2n_16r": {"-n 90": "17.6 s", "-n 150": "27.3 s", "-n 240": "70.8 s"},
        "target_1_3_min": "flux run -N 2 -n 16 <build>/amg -P 4 2 2 -n 240 240 240 -problem 1",
    },
    "variants": {},
    "notes": [
        "startup-dominated at small sizes: 4.6x unknowns (n 90 -> 150) bought 1.55x wall time",
        "PAPI multiplex is context-dependent: 0 on compute nodes, 1 on a login node for the same 4 presets; read it from the trace",
        "expected-absent: GPU KERNEL_DISPATCH/MEMORY_COPY (CPU build), HDF5, CPU/RAPL power (MSR denied to non-root)",
    ],
}

RULES = [
    {"id": "use_cmake_not_makefile", "forbid": r"\bmake\b.*HYPRE_DIR=",
     "why": "the hand-edited Makefile hardcodes HYPRE_DIR to a home directory and links CUDA/Umpire paths that do not exist",
     "fix": "configure with cmake -DHYPRE_PREFIX=<session hypre> -DAMG_WITH_MPI=TRUE -DAMG_WITH_OMP=TRUE"},
    {"id": "out_of_source", "forbid": r"\bcmake\s+\.(\s|$)|\bcmake\s+-S\s*(\S+)\s+-B\s*\1(\s|$)",
     "why": "CMakeLists.txt refuses an in-source build", "fix": "configure out-of-source (-S <source> -B <build>)"},
    {"id": "hypre_prefix", "require": r"-DHYPRE_PREFIX=", "when": r"-DAMG_WITH_(MPI|OMP)",
     "why": "AMG2023 needs the session-built hypre >= 2.27.0", "fix": "pass -DHYPRE_PREFIX=<session hypre prefix>"},
    {"id": "hypre_version", "forbid": r"hypre.*--branch\s+v2\.(?:[0-9]|1[0-9]|2[0-6])\.\d+",
     "why": "AMG2023 needs hypre >= 2.27.0", "fix": "clone hypre v2.32.0"},
    {"id": "hypre_openmp", "require": r"--with-openmp", "when": r"\./configure\b.*--with-MPI",
     "why": "the CPU MPI+OpenMP build needs hypre configured with OpenMP", "fix": "configure hypre with --with-MPI --with-openmp --enable-shared"},
    {"id": "verify_hypre_config", "require": r"HYPRE_config\.h", "when": r"\./configure\b.*--with-MPI",
     "why": "configure's exit code does not prove the config took", "fix": "grep HYPRE_USING_OPENMP/HYPRE_SEQUENTIAL in <hypre>/include/HYPRE_config.h"},
    {"id": "link_core", "forbid": r"-ldftracer(?![_\w])",
     "why": "session_patch_build links -ldftracer, which does not exist; FUNCTION mode needs libdftracer_core.so",
     "fix": "patch target_link_libraries to -ldftracer_core"},
    {"id": "no_hypre_annotation", "forbid": r"clang_annotate_(project|file)\S*.*hypre",
     "why": "hypre kernels run O(10^9) times per solve; annotating them dominates runtime and trace volume", "fix": "annotate only amg.c"},
    {"id": "no_map27", "forbid": r"hypre_map27.*(annotate|DFTRACER)",
     "why": "hypre_map27 is a 6-line mapper in the innermost assembly loop", "fix": "leave hypre_map27 cost-filtered"},
]

_LAUNCH = re.compile(r"\b(?:flux\s+(?:run|submit|batch)|srun|mpirun|mpiexec)\b(.*?)\s(\S*\bamg)(\s.*|$)")


def _p_checks(commands):
    """p*q*r must equal the rank count, else 'Error: Invalid number of processors or processor topology' and exit(1)."""
    out = []
    for c in _commands(commands):
        m = _LAUNCH.search(c)
        if not m:
            continue
        n = None
        for rx in (r"(?:^|\s)-n\s*(\d+)\b", r"--ntasks[= ](\d+)", r"(?:^|\s)-np\s+(\d+)"):
            k = re.search(rx, " " + m.group(1))
            if k:
                n = int(k.group(1))
                break
        p = re.search(r"\s-P\s+(\d+)\s+(\d+)\s+(\d+)", m.group(3))
        if n is None or not p:
            continue
        prod = int(p.group(1)) * int(p.group(2)) * int(p.group(3))
        ok = prod == n
        out.append({"check": "p_matches_ranks", "ok": ok,
                    "detail": "ok" if ok else f"-P product {prod} != {n} ranks: 'Invalid number of processors or processor topology'",
                    "fix": "" if ok else "choose -P p q r with p*q*r equal to the rank count"})
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
    def workload_amg2023_recipe(variant: str = "") -> dict:
        """Predictor: the AMG2023 recipe dftracer-agents verified: hypre v2.32.0 from source (MPI+OpenMP, shared) with the
        HYPRE_config.h check, the out-of-source CMake configure, the -ldftracer_core link fix, the 3-function annotation scope and
        main() INIT/FINI layout around hypre_MPI_Init/Finalize, and run sizing (-P, -n per rank). variant: optional (none
        defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_amg2023_check(commands: list) -> dict:
        """Validator: check a proposed AMG2023 recipe or command list against the skill's rules: CMake not the Makefile,
        out-of-source, -DHYPRE_PREFIX, hypre >= 2.27 with --with-openmp and a HYPRE_config.h check, -ldftracer_core, no hypre or
        hypre_map27 annotation, and -P p q r whose product equals the launcher's rank count. commands: list of shell lines (or
        newline/JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _p_checks(commands)
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res
