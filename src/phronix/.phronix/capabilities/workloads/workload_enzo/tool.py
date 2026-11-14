"""workload_enzo: the Enzo (enzo-project/enzo-dev enzo-2.6.1, AMR cosmology, C++ .C + Fortran, MPI) build/annotate/run
recipe that dftracer-agents' workload-enzo skill verified on Tuolumne, as structured data (predictor), and a deterministic
check of a proposed recipe or command list against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_enzo"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "Enzo",
    "what": "AMR hydro + N-body cosmology code; traced scientific workload",
    "repo": "https://github.com/enzo-project/enzo-dev",
    "ref": "enzo-2.6.1",
    "build_system": "custom Make (./configure at repo root, then gmake in src/enzo); not CMake/autotools",
    "languages": {"src/enzo": "~951 .C (C++), 9 .c, ~150 Fortran (.F, .F90), plus uuid/ C; all MPI/IO/driver logic is in the .C files"},
    "systems": ["tuolumne"],
    "inputs": {
        "configs": "victoriastodden/ComputationalUncertaintyHPC -> <N>-<L>-10Mpc-z0/Init",
        "param_file": "gas_plus_dm_amr_multiphys.enzo",
        "initial_conditions": "HDF5: GridDensity, GridVelocities, ParticlePositions, ParticleVelocities",
        "placement": "copy Init/ onto the PFS (<WS>/dataset/<run>/) and run from there",
    },
    "dependencies": {
        "hdf5": "HDF5 1.10.x from source (1.10.11 used)",
        "grackle": "not needed (configs use internal MultiSpecies=1 cooling): grackle-no",
    },
    "make_mach": {
        "file": "Make.mach.tuolumne (write it yourself)",
        "CC/CXX": "Cray mpicc / mpicxx",
        "FC": "gcc-toolset-13 gfortran",
        "rpath": "to HDF5 and libgfortran",
        "MACH_LIBS": "carries a $(DFTRACER_LIBS) hook",
    },
    "source_fixes": [
        "Grid_CreateParticleTypeGrouping.C:68: `reference` -> `&reference` (H5Dwrite arg) (Cray-clang 20)",
        "ListIO.C: \"...\"__FILE__ -> \"...\" __FILE__ (C++11 needs the space) (Cray-clang 20)",
    ],
    "configure": ["./configure"],
    "build": [
        "cd src/enzo && gmake machine-tuolumne opt-aggressive use-mpi-yes grackle-no",
        "gmake -j32",
    ],
    "build_annotated": [
        "gmake clean   # copying source/ to annotated/ also copies the baseline .o files",
        "gmake MACH_INCLUDES=\"-I$HDF5_DIR/include -I<dftracer>/include\" "
        "DFTRACER_LIBS=\"-L<dftracer>/lib64 -Wl,-rpath,<dftracer>/lib64 -ldftracer_core\" -j32",
    ],
    "annotate": {
        "call": "clang_annotate_project(language=\"cpp\", cpp_extensions=[\".C\"])",
        "exclude_dirs": ["/src/anyl/", "/src/enzohop/", "/src/inits/", "/src/lcaperf/", "/src/mpgrafic/",
                         "/src/performance_tools/", "/src/P-GroupFinder/", "/src/ring/"],
        "exclude_files": ["auto_show_flags.C"],
        "clang_flags": "the build's DEFINES (make show-flags) + -Wno-everything -Wno-c++11-narrowing -Wno-reserved-user-defined-literal",
        "c_files": "do not pass -std=c++14 to the 20 .c files (they then fail to parse); hot deposit/interp kernels + uuid, fine unannotated",
        "first_include": "dftracer.h must be the FIRST include (macros_and_parameters.h #defines int long_int, float double)",
        "entry": "main is `Eint32 MAIN_NAME(...)` with #define MAIN_NAME main: entry detection must follow the macro",
        "fini": "DFTRACER_CPP_FINI(); inside my_exit() immediately before CommunicationFinalize(); (enzo.C, success branch)",
        "pre_main_ctors": "re-annotate ActiveParticleRoutines.C with exclude_functions=[\"ActiveParticleType\"] and "
                          "StochasticForcing_constructor.C with exclude_functions=[\"StochasticForcing\"]",
        "restore_unannotated": ["RadiativeTransferHealpixRoutines64.C"],
    },
    "env": {
        "DFTRACER_ENABLE": "1", "DFTRACER_INIT": "FUNCTION", "DFTRACER_INC_METADATA": "1", "DFTRACER_DATA_DIR": "all",
        "DFTRACER_TRACE_COMPRESSION": "1",
    },
    "env_callstack_mpi_only": {"DFTRACER_DISABLE_POSIX": "1", "DFTRACER_DISABLE_STDIO": "1"},
    "smoke": ["echo 'StopCycle = 10' >> gas_plus_dm_amr_multiphys.enzo",
              "enzo.exe -d gas_plus_dm_amr_multiphys.enzo   # 1 process, ~0.8 s"],
    "run": ["enzo.exe -d gas_plus_dm_amr_multiphys.enzo   # from the copy of Init/ on the PFS"],
    "run_sizing": [
        {"config": "16-3 (16^3)", "layout": "1N x 32", "result": "full run z=99->0, 320 cycles, 560 s, 12 RD outputs"},
        {"config": "16-3 (16^3)", "layout": "4N x 64 (256 ranks)",
         "result": "NaN 'Error interpolating field 1 (x-velocity)' at cycle 109 (z~18.9), MPI_Abort: ~16 cells/rank too few"},
        {"config": "32-7 (32^3)", "layout": "2N x 32", "result": "did NOT finish in 12 min (cycle 186, z~5.35)"},
    ],
    "max_ranks": {"16-3": 32},
    "event_volume": [
        {"run": "16-3, 1N x 32, full", "events": "358 M", "cpp_app": "324 M", "p2p": "26.6 M", "collective": "1.4 M",
         "env": "5.8 M", "size": "3.0 GB"},
        {"run": "32-7, 2N x 32, to z~5.35", "events": "585 M", "cpp_app": "539 M", "p2p": "25.3 M", "collective": "6.6 M",
         "env": "14.2 M", "size": "4.9 GB"},
    ],
    "hot_names": ["search_lower_bound", "CheckForOverlap", "CheckForPossibleOverlapHelper", "CommunicationShouldExit",
                  "CommunicationSendRegion", "CopyZonesFromGrid", "UpdateStarParticles (32^3, 56 M)", "FindNewStarParticles (32^3, 56 M)"],
    "count_events": "dftracer_stats -d <dir> --index-dir <idx> --report categories|top-names",
    "variants": {},
    "notes": [
        "MPI events appear under categories p2p, collective, comm, env (MPI_Wtime), datatype: not one MPI category",
        "brace insertion is skipped on most files (its clang parse lacks the project defines): harmless, DFTRACER_CPP_FUNCTION is RAII",
        "the main region event is never emitted (exit via my_exit); child functions are all traced",
        "use 32-7 (or larger) for multi-node scaling; keep 16-3 at <=32 ranks",
        "256-rank NaN root cause (over-decomposition vs opt-aggressive) not proven: an un-annotated baseline at the same layout would settle it",
    ],
}

RULES = [
    {"id": "grackle_no", "require": r"grackle-no", "when": r"\bgmake\b.*machine-",
     "why": "the ComputationalUncertaintyHPC configs need no Grackle (internal MultiSpecies=1 cooling)",
     "fix": "gmake machine-tuolumne opt-aggressive use-mpi-yes grackle-no"},
    {"id": "use_mpi", "require": r"use-mpi-yes", "when": r"\bgmake\b.*machine-",
     "why": "Enzo runs here are MPI runs", "fix": "add use-mpi-yes to the gmake machine line"},
    {"id": "no_cmake", "forbid": r"^\s*cmake\b|\s-DCMAKE_",
     "why": "Enzo uses its own Make system (./configure, gmake machine-<mach>), not CMake",
     "fix": "write Make.mach.tuolumne and use gmake machine-tuolumne ..."},
    {"id": "hdf5_110", "forbid": r"hdf5[-_/]?1\.1[1-9]|hdf5[-_/]?1\.12|hdf5[-_/]?1\.14",
     "why": "the verified recipe uses HDF5 1.10.x from source (1.10.11)", "fix": "build HDF5 1.10.11 from source"},
    {"id": "cpp_extensions", "require": r"cpp_extensions.*\.C\b", "when": r"clang_annotate_project",
     "why": ".C files are C++: without cpp_extensions=['.C'] the annotator misses ~951 files",
     "fix": "clang_annotate_project(language='cpp', cpp_extensions=['.C'])"},
    {"id": "no_cxx14_on_c", "forbid": r"-std=c\+\+14.*\.c\b(?!\w)",
     "why": "the 20 .c files fail to parse with -std=c++14", "fix": "leave the .c files unannotated"},
    {"id": "clean_before_annotated", "require": r"gmake\s+clean|make\s+clean", "when": r"DFTRACER_LIBS=|MACH_INCLUDES=.*dftracer",
     "why": "copying source/ to annotated/ also copies the baseline .o files", "fix": "gmake clean before the first annotated build"},
    {"id": "dftracer_libs_hook", "require": r"-ldftracer_core", "when": r"MACH_INCLUDES=.*dftracer",
     "why": "the annotated build must link libdftracer_core through the $(DFTRACER_LIBS) hook",
     "fix": "DFTRACER_LIBS=\"-L<dftracer>/lib64 -Wl,-rpath,<dftracer>/lib64 -ldftracer_core\""},
    {"id": "rank_limit_16_3", "forbid": r"16-3.*-n\s*(?:3[3-9]|[4-9]\d|\d{3,})\b|-n\s*(?:3[3-9]|[4-9]\d|\d{3,})\b.*16-3",
     "why": "16-3 at 256 ranks NaNs at cycle 109 ('Error interpolating field 1'): ~16 cells/rank too few",
     "fix": "keep 16-3 at <=32 ranks; use 32-7 or larger for multi-node scaling"},
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
    def workload_enzo_recipe(variant: str = "") -> dict:
        """Predictor: the Enzo (enzo-2.6.1) build/annotate/run recipe dftracer-agents verified on Tuolumne (Make.mach, gmake
        targets, HDF5 1.10.11, Cray-clang source fixes, annotated-build hooks, annotation traps, dftracer env, smoke, rank
        limits and event volumes) as structured JSON. Use before building, annotating or running Enzo. variant: optional
        (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_enzo_check(commands: list) -> dict:
        """Validator: check a proposed Enzo recipe or command list against the skill's rules (grackle-no, use-mpi-yes, no
        CMake, HDF5 1.10.x, cpp_extensions ['.C'], no -std=c++14 on .c, gmake clean before the annotated build, -ldftracer_core
        hook, 16-3 at <=32 ranks). commands: list of shell lines (or a newline-separated string / JSON text). Returns
        {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
