"""workload_amg: the AMG (LLNL/AMG, hypre-based algebraic-multigrid proxy app, ISO-C, MPI+OpenMP, plain Makefile) build,
annotation and run recipe dftracer-agents' workload-amg skill verified on Tuolumne, as structured data (predictor, incl. the
-P decomposition derived from a rank count), and a deterministic check of a proposed recipe or command list against that
skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_amg"

# balanced binary factorisation 2^k -> (2^a, 2^b, 2^c), a >= b >= c; reproduces ice4hpc's 1 -> 1 1 1 and 32 -> 4 4 2
P_TABLE = {1: "1 1 1", 2: "2 1 1", 4: "2 2 1", 8: "2 2 2", 16: "4 2 2", 32: "4 4 2", 64: "4 4 4", 128: "8 4 4",
           256: "8 8 4", 512: "8 8 8"}

RECIPE = {
    "app": "AMG",
    "repo": "LLNL/AMG",
    "what": "parallel algebraic-multigrid solver proxy app on a trimmed copy of hypre; ISO-C, MPI + OpenMP threading within "
            "ranks, decomposed as a logical P x Q x R grid of equal chunks; driver test/amg.c; libraries in utilities/ krylov/ "
            "IJ_mv/ parcsr_ls/ parcsr_mv/ seq_mv/; 84 .c files",
    "build_system": "make (hand-written Makefiles; every subdirectory includes ../Makefile.include)",
    "systems": ["tuolumne"],
    "modules": ["<site MPI/compiler modules>"],
    "env": {"CC": "$(which mpicc)"},
    "default_include_cflags": "-O2 -DTIMER_USE_MPI -DHYPRE_USING_OPENMP -fopenmp -DHYPRE_HOPSCOTCH -DHYPRE_USING_PERSISTENT_COMM -DHYPRE_BIGINT",
    "source_fixes": [
        "add to parcsr_ls/HYPRE_parcsr_ls.h next to HYPRE_BoomerAMGSetNumPaths: "
        "HYPRE_Int HYPRE_BoomerAMGGetCumNnzAP(HYPRE_Solver solver, HYPRE_Real *cum_nnz_AP);  "
        "(clang >= 15 / Cray clang 20: 'call to undeclared function HYPRE_BoomerAMGGetCumNnzAP'; never -Wno-implicit-function-declaration)",
    ],
    "build": ["export CC=$(which mpicc)", "make -j 8 2>&1 | tee build.log",
              "grep -c \"error:\" build.log   # must be 0 (top-level make exits 0 even when subdirs fail)",
              "ls -la test/amg                 # must exist"],
    "dftracer_link": {
        "file": "Makefile.include (the single integration point; session_patch_build's AM_* flags are a silent no-op here)",
        "INCLUDE_CFLAGS": "...existing... $(DFTRACER_CFLAGS)",
        "INCLUDE_LFLAGS": "-lm -fopenmp $(DFTRACER_LDFLAGS) -ldftracer_core",
        "verify": "ldd test/amg | grep dftracer",
    },
    "annotation": {
        "entry_point": "clang_annotate_project always excludes /test/: then clang_annotate_file(filepath='source/test/amg.c', is_entry=True)",
        "init_fini": "move DFTRACER_C_INIT (+FUNCTION_START + comp UPDATE) to right AFTER hypre_MPI_Init(&argc, &argv) (~line 145); "
                     "DFTRACER_C_FINI() BEFORE hypre_MPI_Finalize(); FUNCTION_END->FINI on main's exit(1) and two return(-1), "
                     "and FINI on the exit(1) of the P*Q*R != num_procs check in the grid builder",
        "compile_flags": "-I<ann>/source -I<ann>/source/utilities -I<ann>/source/IJ_mv -I<ann>/source/seq_mv -I<ann>/source/parcsr_mv "
                         "-I<ann>/source/parcsr_ls -I<ann>/source/krylov -I<cray-mpich>/include -DHYPRE_BIGINT -DTIMER_USE_MPI "
                         "-DHYPRE_USING_OPENMP -DHYPRE_HOPSCOTCH -DHYPRE_USING_PERSISTENT_COMM -DHYPRE_TIMING",
        "check_flags": "clang -fsyntax-only $FLAGS <file>.c must be silent",
        "exclude_files": ["utilities/binsearch.c", "utilities/hypre_hopscotch_hash.c", "utilities/hypre_qsort.c",
                          "utilities/hypre_merge_sort.c", "utilities/qsplit.c", "utilities/threading.c", "utilities/timer.c",
                          "utilities/hypre_complex.c", "utilities/random.c", "utilities/hypre_error.c", "utilities/hypre_printf.c",
                          "utilities/amg_linklist.c", "utilities/hypre_prefix_sum.c", "utilities/mpistubs.c",
                          "utilities/umalloc_local.c", "utilities/memory_dmalloc.c"],
        "exclude_functions": ["hypre_qsort2abs (parcsr_ls/par_interp.c:3187, 72% of C_APP events)",
                              "hypre_CSRMatrixGetLoadBalancedPartitionBoundary (131,444 events)"],
        "metadata_from_main": ["problem_id", "solver_id", "max_iter", "mg_max_iter", "coarsen_type", "relax_type", "num_sweeps",
                               "agg_num_levels", "P_max_elmts", "num_functions", "time_steps",
                               "ranks via local hypre_MPI_Comm_size(hypre_MPI_COMM_WORLD, &n)"],
        "metadata_value": "DFTRACER_C_METADATA value is const char*: hypre_sprintf(dft_mbuf, \"%d\", (int)(x)) first",
        "include_position": "the dftracer include line must be LOWER than the first DFTRACER_C_ line in every file",
        "braceless_bodies": "verify no FUNCTION_END between a braceless if/else/for head and its body (skip blank lines looking back)",
    },
    "run": {
        "args": "-P p q r (product = rank count) -n nx ny nz (grid PER RANK) -problem 1|2",
        "smoke": "1 rank: -P 1 1 1 -n 20 20 20 -problem 1 (~1 s)",
        "baseline": "flux run -N 2 -n 8 -c 20 env OMP_NUM_THREADS=8 <ann>/test/amg -P 2 2 2 -n 100 100 100 -problem 1 (13 s, 1,318,447 events)",
        "invariants": {"Iterations": 17, "Final Relative Residual Norm": "6.589910e-09",
                       "for": "-P 1 1 1 -n 20 20 20 -problem 1, annotated with DFTRACER_ENABLE=0"},
        "papi": "PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS is exact on MI300A (multiplex=0)",
    },
    "p_table": P_TABLE,
    "aggregation": {"env": {"DFTRACER_ENABLE_AGGREGATION": "1", "DFTRACER_AGGREGATION_TYPE": "SELECTIVE"},
                    "rule": "dur < 100 excluding categories collective, comm, p2p (fold the app layer, never MPI)",
                    "count_field": "dft_cnt (never count: POSIX read/write use count for bytes)"},
    "peak_rss_per_rank": {"p1_n8x8x4": "30 MB", "p1_n32x32x16": "47 MB", "p1_n64x64x32": "166 MB", "p1_n128x128x64": "1.10 GB",
                          "p2_n16x16x16": "38 MB", "p2_n32x32x32": "91 MB", "p2_n64x64x32": "273 MB", "p2_n64x64x64": "515 MB",
                          "p2_n128x128x64": "1.94 GB", "p2_n128x128x128": "3.85 GB", "p2_n256x256x256": "30.8 GB"},
    "variants": {},
    "notes": [
        "AMG is FAST: a multi-minute run is more likely a Flux job in state S waiting for cores held by dftracer_service: flux jobs -a",
        "at high rank counts on a small per-rank grid the trace is a p2p firehose (Iprobe/Testall): p2_n8x8x8 @128 ranks 384 M events; bytes ~ ranks^1.4-1.9",
        "GPU KERNEL_DISPATCH/MEMORY_COPY absent by design (CPU-only); gpu-category records come from variorum in the service trace",
        "sweeps: treat (problem, -n) as the input and DERIVE -P per rank count (p_table); never sweep -P",
    ],
}

RULES = [
    {"id": "no_wno_implicit", "forbid": r"-Wno-implicit-function-declaration",
     "why": "HYPRE_BoomerAMGGetCumNnzAP is only undeclared in the public header; silencing the error hides the real fix",
     "fix": "add the HYPRE_BoomerAMGGetCumNnzAP prototype to parcsr_ls/HYPRE_parcsr_ls.h"},
    {"id": "gate_on_artifact", "require": r"test/amg\b|grep\s+-c\s+[\"']?error:", "when": r"(^|[;&|]\s*)make\b(?!\s+clean)",
     "why": "the top-level make loops over HYPRE_DIRS without error propagation and exits 0 when subdirectory builds fail",
     "fix": "after make, grep -c \"error:\" build.log (must be 0) and ls -la test/amg"},
    {"id": "link_core", "forbid": r"-ldftracer(?![_\w])",
     "why": "the FUNCTION-mode library is libdftracer_core; -ldftracer does not exist", "fix": "link -ldftracer_core"},
    {"id": "makefile_include_wiring", "require": r"INCLUDE_LFLAGS|-ldftracer_core", "when": r"session_patch_build|DFTRACER_LDFLAGS|DFTRACER_CFLAGS",
     "why": "session_patch_build injects AM_CPPFLAGS/AM_LDFLAGS that AMG's hand-written Makefiles never read (silent no-op)",
     "fix": "append $(DFTRACER_CFLAGS) to INCLUDE_CFLAGS and $(DFTRACER_LDFLAGS) -ldftracer_core to INCLUDE_LFLAGS in Makefile.include"},
    {"id": "entry_point_annotated", "require": r"test/amg\.c", "when": r"clang_annotate_project",
     "why": "clang_annotate_project always excludes /test/, so main() gets no DFTRACER_C_INIT/FINI",
     "fix": "add clang_annotate_file(filepath='source/test/amg.c', is_entry=True) after the project pass"},
    {"id": "annotate_include_paths", "require": r"-I\S*utilities", "when": r"clang_annotate_(project|file)",
     "why": "without include paths clang falls back to an error-recovery AST: 251 instead of 388 functions annotated, status still ok",
     "fix": "pass compile_flags with -I for source, utilities, IJ_mv, seq_mv, parcsr_mv, parcsr_ls, krylov, cray-mpich include and the -DHYPRE_* defines"},
    {"id": "exclude_qsort2abs", "require": r"hypre_qsort2abs", "when": r"clang_annotate_(project|file)",
     "why": "hypre_qsort2abs (parcsr_ls/par_interp.c) alone produced 733,521 of 1,023,178 C_APP events (72%)",
     "fix": "add hypre_qsort2abs (and hypre_CSRMatrixGetLoadBalancedPartitionBoundary) to exclude_functions"},
    {"id": "aggregation_spares_mpi", "require": r"p2p", "when": r"dur\s*<\s*\d+",
     "why": "dur<100 on everything kept only 2,421 of 140,392 p2p events: it destroys what an AMG trace is for",
     "fix": "apply the dur<100 rule excluding categories collective, comm, p2p"},
    {"id": "fold_count_field", "forbid": r"\bargs\.count\b|\[[\"']count[\"']\]",
     "why": "aggregated fold counts are in dft_cnt; POSIX read/write already use count for syscall bytes", "fix": "read dft_cnt"},
]

_LAUNCH = re.compile(r"\b(?:flux\s+(?:run|submit|batch)|srun|mpirun|mpiexec)\b(.*?)\s(\S*\bamg)(\s.*|$)")


def _ranks(launcher_args):
    for rx in (r"(?:^|\s)-n\s*(\d+)\b", r"--ntasks[= ](\d+)", r"(?:^|\s)-np\s+(\d+)"):
        m = re.search(rx, " " + launcher_args)
        if m:
            return int(m.group(1))
    return None


def _p_checks(commands):
    """-P p q r must multiply to the launcher's rank count (else 'Invalid number of processors or processor topology', exit(1))."""
    out = []
    for c in _commands(commands):
        m = _LAUNCH.search(c)
        if not m:
            continue
        n = _ranks(m.group(1))
        p = re.search(r"\s-P\s+(\d+)\s+(\d+)\s+(\d+)", m.group(3))
        if n is None or not p:
            continue
        prod = int(p.group(1)) * int(p.group(2)) * int(p.group(3))
        ok = prod == n
        out.append({"check": "p_matches_ranks", "ok": ok,
                    "detail": "ok" if ok else f"-P {p.group(1)} {p.group(2)} {p.group(3)} = {prod} != {n} ranks: the app exits 1",
                    "fix": "" if ok else f"derive -P from the rank count: {P_TABLE.get(n, 'balanced binary factorisation')}"})
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
    def workload_amg_recipe(variant: str = "", ranks: int = 0) -> dict:
        """Predictor: the AMG (LLNL/AMG, hypre proxy) recipe dftracer-agents verified: build with make + artifact gate, the
        HYPRE_BoomerAMGGetCumNnzAP header fix, Makefile.include dftracer wiring, annotation flags/exclusions/INIT-FINI placement,
        run sizing, invariants, aggregation and per-rank memory. variant: optional (none defined). ranks: if > 0, also return
        the derived -P decomposition for that rank count (balanced binary factorisation). Returns {status, capability, recipe,
        rules, p_for_ranks}."""
        out = _recipe(variant)
        if ranks and out.get("status") == "ok":
            r = int(ranks)
            out["p_for_ranks"] = P_TABLE.get(r) or ("not a power of two in 1..512: factor ranks into p>=q>=r as evenly as possible")
        return out

    @mcp.tool()
    def workload_amg_check(commands: list) -> dict:
        """Validator: check a proposed AMG recipe or command list against the skill's rules: no -Wno-implicit-function-declaration,
        gate make on test/amg / build.log errors, -ldftracer_core via Makefile.include, entry point test/amg.c annotated, include
        paths and hypre_qsort2abs exclusion for annotation, aggregation that spares p2p/comm/collective, dft_cnt, and -P p q r
        whose product equals the launcher's rank count. commands: list of shell lines (or newline/JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _p_checks(commands)
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res
