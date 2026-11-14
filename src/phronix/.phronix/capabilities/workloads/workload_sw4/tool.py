"""workload_sw4: the SW4 (geodynamics/sw4, 4th-order 3D seismic wave propagation, C++ + Fortran-77, MPI+OpenMP) build,
annotation and run recipe that dftracer-agents' workload-sw4 skill verified on a Cray/MI300A system, as structured data
(predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator).
Nothing here runs a build or a job."""
import json
import re

CAP = "workload_sw4"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "SW4",
    "repo": "https://github.com/geodynamics/sw4",
    "what": "Seismic Waves, 4th order accuracy: finite-difference elastic/anelastic wave propagation on Cartesian and curvilinear grids",
    "build_system": "make (Makefile; CMakeLists.txt exists and session_detect reports cmake, but the Makefile is the maintained, simpler path)",
    "languages": ["C++ (121 .C + 79 .h)", "Fortran-77 (25 .f: 23 QUADPACK + rayleighfort.f + lamb_exact_numquad.f, support code only)"],
    "systems": ["tuolumne (MI300A/Cray PE)"],
    "dependencies": ["MPI", "LAPACK (dgetrf, dgetrs, dgesv, dgels) via Cray libsci: -lsci_cray_mp"],
    "optional_off": ["proj", "hdf5", "fftw", "zfp", "sz"],
    "make_inc": [
        "proj = no", "hdf5 = no", "fftw = no", "zfp  = no", "sz   = no", "openmp = yes",
        "CXX = <mpic++>", "FC  = <ftn>",
        "EXTRA_LINK_FLAGS = -fopenmp -L$(CRAY_LIBSCI_PREFIX_DIR)/lib -lsci_cray_mp -Wl,-rpath,$(CRAY_LIBSCI_PREFIX_DIR)/lib",
    ],
    "build": [
        "write configs/make.inc (above; auto-included, overrides the hostname dispatch block)",
        "delete the '#pragma ivdep' line that precedes '#pragma omp simd' at the 6 sites in GridGenerator.C and rhs4curvilinearc.C (Cray clang)",
        "make   # default openmp=yes prec=double; build dir optimize_mp/",
    ],
    "annotate": {
        "prepare": "rename src/*.C -> src/*.cpp in the annotated tree and update the 4 .C references in the Makefile "
                   "(src/rhs4sgcurv.C, src/version.C, the %.o:src/%.C pattern rule, src/RandomizedMaterial.C); build the renamed pristine tree first",
        "language": "cpp (always pass explicitly)",
        "compile_flags": "-std=c++11 -I<annotated>/src -I<annotated>/src/double -I<mpi include dir>",
        "exclude_functions": ["getDepth"],
        "never_annotate": ["Sarray.h", "Farray.h"],
        "post_checks": [
            "include line < first DFTRACER_CPP_ line (EW.C, RandomizedMaterial.C)",
            "INIT/REGION_START/REGION_DYN_UPDATE in main.C right after MPI_Comm_rank (above the 3 argument-error exits)",
            "repair brace-pass corruption (fastmarching.C, sacsubc.C) by diffing against pristine",
        ],
        "coverage": "121 C++ files -> 112 annotated, 1059 spans, 1059 comp= UPDATEs",
    },
    "run": {
        "input": "copy examples/scec/LOH.1-h50.in, coarsen h and shorten time t",
        "sizing": [
            {"h": 400, "points": "0.25 M", "t": 1.0, "steps": 15, "wall": "~1.5 s (1 rank)"},
            {"h": 100, "points": "15.5 M", "t": 3.0, "steps": 179, "wall": "16 s (2 nodes)"},
            {"h": 75, "points": "36.7 M", "t": 9.0, "steps": 715, "wall": "89-112 s (2 nodes)"},
        ],
        "launch": "flux run -N2 -n16 -c11 env OMP_NUM_THREADS=11 <sw4> <input.in>",
        "input_lines": ["fileio path=<parallel filesystem dir>", "rec ... usgsformat=1", "image mode=... timeInterval=..."],
    },
    "variants": {},
    "notes": [
        "libsci is NOT auto-linked by mpicc/mpic++ from the Cray MPICH bin dir (only cc/CC/ftn wrappers): link -lsci_cray_mp explicitly",
        "mixed C++/Fortran linkage needs nothing special with CCE",
        "SW4 does real POSIX I/O (117 files / 65 MB at h=75): missing POSIX events are a defect",
        "verify pristine, annotated DFTRACER_ENABLE=0 and traced runs give byte-identical stdout (modulo compile banner) and receiver files",
    ],
}

RULES = [
    {"id": "no_ivdep_before_omp_simd", "forbid": r"#pragma\s+ivdep",
     "why": "Cray clang: 'error: expected a for, while, or do-while loop to follow ivdep' when #pragma ivdep precedes #pragma omp simd",
     "fix": "delete the '#pragma ivdep' lines (omp simd already asserts independence)"},
    {"id": "libsci_linked", "require": r"-lsci_cray(_mp)?\b", "when": r"\bmake\b|EXTRA_LINK_FLAGS|mpic\+\+",
     "why": "LAPACK (dgetrf/dgetrs/dgesv/dgels) comes from Cray libsci, which mpic++ does not auto-link",
     "fix": "add -L$(CRAY_LIBSCI_PREFIX_DIR)/lib -lsci_cray_mp -Wl,-rpath,... to EXTRA_LINK_FLAGS"},
    {"id": "optional_deps_off", "forbid": r"^\s*(proj|hdf5|fftw|zfp|sz)\s*=\s*yes",
     "why": "SW4 builds cleanly with proj/hdf5/fftw/zfp/sz off; keep dependencies minimal",
     "fix": "set proj/hdf5/fftw/zfp/sz = no in configs/make.inc"},
    {"id": "use_makefile", "forbid": r"\bcmake\b",
     "why": "the Makefile is SW4's maintained path; session_detect's 'cmake' only reflects a CMakeLists.txt",
     "fix": "build with make and configs/make.inc"},
    {"id": "annotate_language_cpp", "forbid": r"language\s*=\s*[\"']?(c|auto)[\"']?\b(?!\+)",
     "why": "SW4's .C files are parsed as C by source_parser._try_clang (suffix.lower()=='.c'): fails on any C++ construct",
     "fix": "rename .C -> .cpp in the annotated tree and pass language=\"cpp\""},
    {"id": "exclude_getDepth", "require": r"getDepth", "when": r"clang_annotate_(file|project)",
     "why": "EW::getDepth is called once per grid point: 97% of app events, wall 1.37 s -> 3.86 s",
     "fix": "pass exclude_functions='[\"getDepth\"]'"},
    {"id": "no_array_headers", "forbid": r"clang_annotate_file\(.*(Sarray|Farray)\.h",
     "why": "Sarray.h/Farray.h are per-element inline accessors, far worse than getDepth", "fix": "do not annotate them"},
    {"id": "omp_threads_match", "require": r"OMP_NUM_THREADS=\d+", "when": r"flux run|srun|mpirun",
     "why": "the validated launch is -N2 -n16 -c11 with OMP_NUM_THREADS=11 (88 of 96 cores, a core left for dftracer_service)",
     "fix": "set OMP_NUM_THREADS equal to -c"},
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
    def workload_sw4_recipe(variant: str = "") -> dict:
        """Predictor: the SW4 recipe dftracer-agents verified - minimal configs/make.inc (no proj/hdf5/fftw/zfp/sz, libsci
        linked), ivdep fix, .C->.cpp annotation prep, compile flags, the getDepth exclusion, LOH.1 run sizing and the 2-node
        launch. variant: optional variant name (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_sw4_check(commands: list) -> dict:
        """Validator: check a proposed SW4 recipe or command list against the skill's rules (no '#pragma ivdep', libsci linked,
        optional deps off, Makefile not CMake, language cpp, getDepth excluded, no Sarray/Farray annotation, OMP threads set).
        commands: list of shell lines / make.inc lines / tool calls (or one newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
