"""workload_smith: the Smith (LLNL/smith, formerly Serac; 3D implicit nonlinear thermal-structural FEM on MFEM, C++20,
CMake+BLT, MPI) from-source build, annotation and run recipe that dftracer-agents' workload-smith skill verified, as
structured data (predictor), and a deterministic check of a proposed recipe or command list against that skill's rules
(validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_smith"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "Smith (formerly Serac, LLNL-CODE-805541)",
    "repo": "https://github.com/LLNL/smith",
    "what": "3D implicit nonlinear thermal-structural simulation code built on MFEM; pre-alpha, some develop targets do not compile",
    "build_system": "cmake + BLT",
    "languages": ["C++20"],
    "systems": ["tuolumne (TOSS4, CPU MPI build)"],
    "tpl_policy": "host-configs/<system>-*.cmake point at a group-gated shared TPL tree (drwxrws---, Permission denied outside the "
                  "group): read them for the validated toolchain and version pins, rebuild the TPLs into the session workspace",
    "codevelop": "-DSMITH_ENABLE_CODEVELOP=ON builds MFEM, Axom, Tribol, gretl, ContinuationSolvers from in-tree submodules",
    "submodules": "git submodule update --init --recursive (axom alone ~277 MB)",
    "tpls_from_source": [
        {"tpl": "METIS 5.1.0", "why": "MFEM (MFEM_USE_METIS_5 hardcoded ON)", "notes": "github.com/mfem/tpls mirror; make config cc=$CC"},
        {"tpl": "ParMETIS 4.0.3", "why": "PARMETIS_DIR is a hard smith_assert_is_directory", "notes": "same mirror"},
        {"tpl": "hypre", "why": "MFEM", "notes": "builds in ~90 s"},
        {"tpl": "HDF5", "why": "Conduit (serial HDF5 is sufficient)", "notes": "build from source, never the Cray module"},
        {"tpl": "camp", "why": "hard FATAL_ERROR if CAMP_DIR unset", "notes": "needs -DBLT_SOURCE_DIR=<smith>/cmake/blt"},
        {"tpl": "Conduit", "why": "hard FATAL_ERROR if CONDUIT_DIR unset", "notes": "BLT lives at <conduit>/src/blt, not <conduit>/blt"},
        {"tpl": "SuperLU_DIST", "why": "not optional: smith::SuperLUSolver is unguarded in equation_solver.hpp", "notes": "needs ParMETIS + BLAS/LAPACK"},
    ],
    "tpls_optional": ["Umpire", "RAJA", "Sundials", "PETSc", "Caliper", "Adiak", "Enzyme", "NetCDF", "STRUMPACK (nearly: guard solid_mechanics_contact.hpp or build it, ~1 h with ScaLAPACK)"],
    "cmake_flags": {
        "SMITH_ENABLE_CODEVELOP": "ON",
        "CMAKE_C_FLAGS / CMAKE_CXX_FLAGS": "--gcc-toolchain=/opt/rh/gcc-toolset-13/root/usr",
        "link rpath": "-Wl,-rpath,<toolset>/lib/gcc/x86_64-redhat-linux/13",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
        "SUPERLUDIST_DIR": "<superlu_dist prefix> (in a FRESH build dir)",
        "METIS_DIR / PARMETIS_DIR / HYPRE_DIR / HDF5_DIR / CAMP_DIR / CONDUIT_DIR": "<session prefixes>",
    },
    "source_patches": [
        "src/CMakeLists.txt and examples/CMakeLists.txt: add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-include$<SEMICOLON>format>)  (~33 sources use std::format without <format>)",
        "src/smith/physics/solid_mechanics_contact.hpp: guard StrumpackSolver with #ifdef MFEM_USE_STRUMPACK, else std::make_unique<SuperLUSolver>(filter_solver_print_level, comm)",
    ],
    "run": {
        "binary": "build/examples/composable_thermo_mechanics (no CLI args; size in source)",
        "other_examples": ["composable_thermo_mechanics_advanced", "composable_solid_mechanics", "simple_conduction", "buckling_cylinder", "bin/partitioner"],
        "sizing": "mfem::Mesh::MakeCartesian3D(80, 20, 20, mfem::Element::HEXAHEDRON, 1.0, 0.1, 0.1) (was 8,2,2); for (int step = 0; step < 5; ++step) (was 2)",
        "shape": "2 nodes x 16 ranks, CPU MPI-only, ~81 s pristine",
    },
    "annotate": {
        "scope": "src/ AND the example's main (otherwise no INIT/FINI: every trace 0 bytes, rc=0)",
        "init": "DFTRACER_CPP_INIT / REGION_START right after the smith::ApplicationManager constructor (it calls MPI_Init); REGION_END -> FINI before the final return",
        "compile_flags": "-I <tree>/src -isystem <tree>/gretl/src -I<dftracer include> plus the rest from compile_commands.json (~20 -isystem paths)",
        "exclude_functions_low_overhead": ["GetElementVDofs"],
    },
    "variants": {},
    "notes": [
        "there is NO smith driver binary: smith_driver is commented out and src/drivers/smith.cpp is stale (12 'no matching constructor' errors)",
        "SMITH_ENABLE_BENCHMARKS=ON fails configure (BLT cannot find a gbenchmark submodule)",
        "parsing one Smith .cpp costs minutes (Axom+MFEM headers): expect client-side MCP timeouts; grep the file before retrying",
        "tracing cost: pristine 81 s, annotated DFTRACER_ENABLE=0 82 s, traced 201 s (2.5x); GetElementVDofs ~61% of app events on rank 0",
        "dftracer_stats --report categories hits 'Events Scanned: 0': use dftracer_reader --mode lines; 'type' is top-level; strip leading [/, and trailing ,",
    ],
}

RULES = [
    {"id": "codevelop_on", "require": r"-DSMITH_ENABLE_CODEVELOP=ON", "when": r"\bcmake\b",
     "why": "codevelop builds MFEM/Axom/Tribol/gretl/ContinuationSolvers in-tree and collapses the TPL stack",
     "fix": "add -DSMITH_ENABLE_CODEVELOP=ON"},
    {"id": "gcc13_toolchain", "require": r"--gcc-toolchain=\S*gcc-toolset-1[3-9]", "when": r"\bcmake\b",
     "why": "Smith uses C++20 std::format; the TOSS4 system libstdc++ is too old",
     "fix": "add --gcc-toolchain=/opt/rh/gcc-toolset-13/root/usr to CMAKE_C_FLAGS/CMAKE_CXX_FLAGS and the gcc 13 lib rpath"},
    {"id": "superlu_dist", "require": r"SUPERLUDIST_DIR=", "when": r"\bcmake\b",
     "why": "smith::SuperLUSolver is declared outside #ifdef MFEM_USE_SUPERLU: smith_numerics does not compile without SuperLU_DIST",
     "fix": "build SuperLU_DIST and pass -DSUPERLUDIST_DIR in a FRESH build directory (MFEM_USE_SUPERLU is a cache set)"},
    {"id": "no_benchmarks", "forbid": r"SMITH_ENABLE_BENCHMARKS=ON",
     "why": "BLT cannot find a gbenchmark submodule and configure fails", "fix": "leave SMITH_ENABLE_BENCHMARKS off"},
    {"id": "no_smith_driver", "forbid": r"\bsmith_driver\b|bin/smith\b",
     "why": "the smith driver target is commented out upstream and src/drivers/smith.cpp is stale",
     "fix": "run an example, best composable_thermo_mechanics"},
    {"id": "no_cray_hdf5", "forbid": r"module\s+load\s+cray-hdf5",
     "why": "HDF5 for Conduit is built from source, never the Cray module", "fix": "build serial HDF5 from source in the session"},
    {"id": "no_group_tpls", "forbid": r"-C\s*\S*host-configs/\S+\.cmake",
     "why": "host-configs point at a group-gated TPL tree (Permission denied outside the group)",
     "fix": "read the host-config for pins only; rebuild the TPLs into the session workspace"},
    {"id": "annotate_src_include", "require": r"-I\s*\S*/src(\s|$|\")", "when": r"clang_annotate_(file|project)",
     "why": "quoted project includes need -I <tree>/src; without it the brace pass self-disables and functions look trivial",
     "fix": "add -I <tree>/src -isystem <tree>/gretl/src and the dftracer include"},
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
    def workload_smith_recipe(variant: str = "") -> dict:
        """Predictor: the Smith (Serac) recipe dftracer-agents verified - codevelop build, the from-source TPL chain
        (METIS, ParMETIS, hypre, HDF5, camp, Conduit, SuperLU_DIST), gcc-toolset-13 flags, the <format> and STRUMPACK patches,
        the runnable example and its in-source sizing, annotation scope and flags. variant: optional (none defined).
        Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_smith_check(commands: list) -> dict:
        """Validator: check a proposed Smith recipe or command list against the skill's rules (codevelop on, gcc 13 toolchain,
        SuperLU_DIST given, no benchmarks, no smith driver, no Cray HDF5 module, no group-gated host-config, -I <tree>/src for
        the annotator). commands: list of shell lines / tool calls (or one newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
