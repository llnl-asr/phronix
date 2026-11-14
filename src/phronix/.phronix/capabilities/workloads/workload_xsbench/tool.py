"""workload_xsbench: the XSBench (ANL-CESAR Monte Carlo cross-section lookup proxy app) build/annotate/run recipe that
dftracer-agents' workload-xsbench skill verified (openmp-threading MPI=yes on CPU, cuda variant on H100), as structured data
(predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator)."""
import json
import re

CAP = "workload_xsbench"

HOT_KERNELS = ["calculate_micro_xs", "calculate_macro_xs", "grid_search", "grid_search_nuclide", "pick_mat", "fast_forward_LCG",
               "LCG_random_double", "quickSort_parallel_internal_i_d", "quickSort_parallel_internal_d_i"]

RECIPE = {
    "app": "XSBench",
    "what": "continuous-energy macroscopic neutron cross-section lookup kernel of Monte Carlo transport (6 C files, ~1500 LOC); "
            "compute/memory-latency bound random gather over a unionized energy grid; essentially no application I/O and almost no MPI",
    "build_system": "make (one Makefile per variant directory; session_detect reports build_tool: unknown)",
    "variants": {
        "openmp-threading": {
            "language": "C", "mpi": "MPI=yes switch in the Makefile", "pick": "default/reference CPU version: pick this for CPU MPI+OpenMP",
            "env": {"CC": "`which mpicc`", "CXX": "`which mpic++`"},
            "build": ["cd <WS>/source/openmp-threading", "make MPI=yes -j8"],
            "annotated_build": ["make MPI=yes -j8 CFLAGS=\"-std=gnu99 -Wall -O3 -fopenmp -DOPENMP -DMPI -I<dft>/include\" "
                                "LDFLAGS=\"-lm -L<dft>/lib64 -ldftracer_core -Wl,-rpath,<dft>/lib64\""],
            "session_install_dftracer": "hip=False, hdf5=False (session_detect false positives from hip/ cuda/ dirs and system h5cc)",
            "makefile_quirks": [
                "MPI=yes overrides CC to the bare string mpicc: mpicc must be on PATH",
                "-flto -fopenmp -DOPENMP only if $(CC) contains gcc/clang/intel (Cray crayclang matches clang); otherwise a serial "
                "un-optimized build: confirm -fopenmp -DOPENMP in the compile lines",
                "overriding CFLAGS drops -flto (harmless, keeps annotated and baseline comparable)",
            ],
            "annotate": {
                "Simulation.c": {"exclude_functions": HOT_KERNELS,
                                 "keep": ["run_event_based_simulation", "run_history_based_simulation",
                                          "run_event_based_simulation_optimization_1"],
                                 "note": "restore the pristine file from source/ before re-annotating"},
                "XSutils.c": "qsort comparators NGP_compare, double_compare stay unannotated (default cost filter skips them)",
                "Main.c": "move INIT/START/metadata out of #ifdef MPI (after MPI_Init); END/FINI unconditional before the #ifdef MPI MPI_Finalize block",
                "io.c": "add DFTRACER_C_FINI() next to the DFTRACER_C_FUNCTION_END() before exit(4) in print_CLI_error()",
            },
        },
        "openmp-offload": {"language": "C", "mpi": "no Makefile switch", "what": "OpenMP 4.5 GPU offload"},
        "cuda": {
            "language": "CUDA", "mpi": "upstream cuda/Main.cu has no MPI (maps.sh app_mpi=0): add MPI_Init/Comm_size/Comm_rank after the "
                                       "declarations and MPI_Finalize before return, both under #ifdef MPI",
            "build": ["make CC=\"nvcc -ccbin g++\" CFLAGS=\"... -arch=sm_90 -DMPI -DMPICH_SKIP_MPICXX -I<mpi>/include -I<dft>/include\" "
                      "LDFLAGS=\"-lm -L<mpi>/lib -lmpi -L<dft>/lib64 -ldftracer_core -Xlinker -rpath ...\""],
            "annotate": "clang_annotate_file on .cu (host-side -xcuda --cuda-host-only; pass --cuda-path=<toolkit> and -D/-I in compile_flags); "
                        "exclude center_print, border_print, fancy_int, logo, double_compare, NGP_compare, rn_v, get_time; re-apply the "
                        "#ifdef MPI INIT/FINI move and print_CLI_error FINI by hand",
            "limits": ["only event mode (-m history exits 1)", "reference checksum only for -s small/-s large at default lookups: XL prints "
                       "INAVALID CHECKSUM and exits 1 on a healthy run", "-s XL -G unionized does not fit an 80 GB H100: sweep XL with hash/nuclide",
                       "full-feature 1-rank -s small ~5 s: ~12 C_APP, 3 CUDA_KERNEL, 7 CUDA_MEMCPY, 2 collective"],
        },
        "hip": {"language": "C++", "mpi": "no Makefile switch: sources have #ifdef MPI but the Makefile never defines -DMPI or links MPI"},
        "opencl": {"language": "C", "mpi": "no"},
        "sycl": {"language": "C++", "mpi": "no"},
    },
    "run": ["./XSBench -m event -s large -l <lookups> -t <threads> -G unionized"],
    "sizing": {
        "-s large": "355 nuclides, 4,012,565 unionized gridpoints, ~5.6 GB per rank (budget per rank)",
        "ranks": "replicas: each rank does all -l lookups (only MPI_Barrier + MPI_Reduce): wall depends on -l and threads, not rank count",
        "grid_init": "~6-8 s (grid_init_do_not_profile)",
        "throughput": "~4.0-5.1 M lookups/s per rank (MI300A CPU, 22 threads): wall ~ 8 s + lookups/4.5e6; -l 200000000 ~55 s",
        "tracing_cost": "full-feature tracing ~21% throughput (5.12 -> 4.04 M lookups/s per rank)",
        "mem_per_rank_MB": {"small": {"unionized": 241, "hash": "~200", "nuclide": "~200"},
                            "large": {"unionized": 5649, "hash": 198, "nuclide": 184},
                            "XL": {"unionized": 119354, "hash": 3895, "nuclide": 3882},
                            "XXL": {"unionized": 250642, "hash": 8165, "nuclide": 8151}},
        "ppn_caps_515GB_node": "XXL-unionized ppn 1, XL-unionized ppn <= 2, XXL-hash/nuclide ppn <= 32; mark the rest SKIPPED up front",
    },
    "checksum": "INVALID CHECKSUM + rc 1 for any non-canonical -l is expected; compare with the unmodified binary (bit-for-bit, e.g. 437675 at -l 200000000)",
}

RULES = [
    {"id": "hot_kernels_excluded", "forbid": r"clang_annotate_(?:project|file)\((?!.*calculate_micro_xs).*Simulation\.c",
     "why": "annotating the per-lookup kernels makes XSBench ~20x slower (18 s run did not finish in 380 s even with DFTRACER_ENABLE=0)",
     "fix": "clang_annotate_file Simulation.c with exclude_functions=" + json.dumps(HOT_KERNELS)},
    {"id": "mpi_yes", "require": r"\bMPI=yes\b", "when": r"\bmake\b(?!.*nvcc)",
     "why": "openmp-threading only enables MPI through its MPI=yes Makefile switch", "fix": "make MPI=yes -j8"},
    {"id": "no_hip_hdf5_install", "forbid": r"session_install_dftracer\(.*(?:hip|hdf5)\s*=\s*True",
     "why": "session_detect reports hip:true (hip/ cuda/ dirs) and hdf5:true (system h5cc) falsely; XSBench uses neither for the CPU variant",
     "fix": "session_install_dftracer(hip=False, hdf5=False)"},
    {"id": "openmp_flags", "require": r"-fopenmp", "when": r"\bmake\b.*CFLAGS=",
     "why": "overriding CFLAGS without -fopenmp -DOPENMP silently yields a serial build", "fix": "include -fopenmp -DOPENMP in CFLAGS"},
    {"id": "mpich_skip_mpicxx", "require": r"-DMPICH_SKIP_MPICXX|-DOMPI_SKIP_MPICXX", "when": r"nvcc.*-DMPI\b",
     "why": "-DMPI under nvcc (C++) with MPICH: 'You cannot define MPI; that name is reserved for the MPI namespace'",
     "fix": "add -DMPICH_SKIP_MPICXX (and -DOMPI_SKIP_MPICXX for OpenMPI)"},
    {"id": "cuda_event_only", "forbid": r"XSBench\b.*-m\s+history.*(?:cuda|nvcc)|(?:cuda|nvcc).*XSBench\b.*-m\s+history",
     "why": "the CUDA variant only implements event mode (-m history exits 1)", "fix": "-m event"},
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
    def workload_xsbench_recipe(variant: str = "") -> dict:
        """Predictor: the XSBench recipe dftracer-agents verified: six variants (openmp-threading is the CPU pick), make MPI=yes
        build and annotated-build flags, Makefile quirks, hot-kernel exclusion list, Main.c/io.c INIT/FINI fixes, run CLI and
        sizing (memory per rank per size/grid), the checksum rule, and the cuda variant's MPI/build/limits. variant: optional
        (e.g. "openmp-threading", "cuda"). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_xsbench_check(commands: list) -> dict:
        """Validator: check a proposed XSBench command list against the skill's rules (hot per-lookup kernels excluded from
        annotation, make MPI=yes, no hip/hdf5 dftracer install, -fopenmp kept in CFLAGS, -DMPICH_SKIP_MPICXX with nvcc -DMPI,
        cuda event mode only). commands: list of shell/tool-call lines (or a newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
