"""workload_minibude: the miniBUDE (UoB-HPC molecular-docking mini-app, C++/CMake, HIP backend on MI300A) build/annotate/run
recipe that dftracer-agents' workload-minibude skill verified, as structured data (predictor), and a deterministic check of
a proposed recipe or command list against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_minibude"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "miniBUDE",
    "what": "Bristol University Docking Engine mini-app: one energy-evaluation kernel (fasten_main) run repeatedly over a fixed pose deck",
    "build_system": "cmake",
    "models": ["serial", "omp", "ocl", "std-indices", "std-ranges", "hip", "cuda", "kokkos", "sycl", "acc", "raja", "tbb", "thrust"],
    "mpi": "NOT an MPI application (no mpi.h, no MPI_ symbol in src/): a '2-node run' is N independent single-process "
           "instances; MPI (and HDF5) trace categories are legitimately absent, never a defect",
    "systems": ["tuolumne (AMD MI300A / gfx942)"],
    "cmake_flags": {
        "CMAKE_BUILD_TYPE": "Release (MANDATORY: CMakeLists has FATAL_ERROR 'Only Release or Debug is supported'; "
                            "session_configure/session_build_annotated default to RelWithDebInfo, so pass it in every call's extra_cmake_flags)",
        "MODEL": "hip",
        "CMAKE_CXX_COMPILER": "<rocm>/bin/hipcc",
        "CXX_EXTRA_FLAGS": "--offload-arch=gfx942 (HIP model sets no arch; hipcc guesses from the build host, wrong on a GPU-less login node)",
    },
    "configure": ["cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DMODEL=hip -DCMAKE_CXX_COMPILER=<rocm>/bin/hipcc "
                  "-DCXX_EXTRA_FLAGS=--offload-arch=gfx942"],
    "configure_annotated": [
        "cmake -S annotated/source -B build_ann -DCMAKE_BUILD_TYPE=Release -DMODEL=hip -DCMAKE_CXX_COMPILER=<rocm>/bin/hipcc "
        "-DCMAKE_CXX_FLAGS=-I<dftracer>/include -DCXX_EXTRA_LIBRARIES=<dftracer>/lib64/libdftracer_core.so "
        "-DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,<dftracer>/lib64 -DCXX_EXTRA_FLAGS=--offload-arch=gfx942",
    ],
    "link_dftracer": [
        "no find_package: CMAKE_PREFIX_PATH injection does nothing; use the project's escape hatches with single-token -D values",
        "cmake --install strips the rpath (Set runtime path ... to \"\"): run from build_ann/, not install_ann/bin/, or re-add LD_LIBRARY_PATH",
    ],
    "build": ["cmake --build build -j"],
    "verified": "MI300A APU: valid: true, max_diff_%: 0.008, ~3780 GFLOP/s at -p 8 -w 64; prefer HIP over omp on AMD GPU (GPU events)",
    "annotate": {
        "layout": "one translation unit: src/main.cpp is the only .cpp; the backend is src/<model>/fasten.hpp (a header)",
        "trap1_main_return": "main ends `return run<USE_PPWI>(...) ? ... : ...;` so REGION_END/FINI land before the work: hoist it: "
                             "`const bool dft_run_ok = run<USE_PPWI>(params, wgsizes, ppwis); DFTRACER_CPP_REGION_END(main); "
                             "DFTRACER_CPP_FINI(); return dft_run_ok ? EXIT_SUCCESS : EXIT_FAILURE;`",
        "trap2_header": "annotator skips headers: add RAII guards by hand to host-side IMPL_CLS::fasten(...) and "
                        "IMPL_CLS::enumerateDevices(); never __global__ fasten_main or checkError; no dftracer include in the header",
        "by_hand_main_cpp": ["readNStruct<T> (deck reader: comp=io and path)", "run<Ns...>"],
        "expected_spans_per_rank": ["main", "run", "parseParams", "readNStruct x4", "evaluate", "fasten", "enumerateDevices",
                                    "selectDevice", "validate", "dumpResults", "showHumanReadable"],
        "expected_span_count": 14,
    },
    "run": ["<build_ann>/bude --deck <annotated tree>/data/bm1 -i 5000 -p 8 -w 64 -o <session Lustre dataset/>/energies.out"],
    "run_sizing": {
        "launches": "-i N gives N + 2 kernel launches (2 warmup)",
        "per_launch": "~13.2 ms at -p 8 -w 64 on MI300A",
        "table": {"~15 s": "-i 1000", "~70 s": "-i 5000", "~130 s": "-i 10000"},
        "csv": "-p/-w accept CSV lists and auto-tune every combination: a 2-element -p list doubles the wall time",
        "output": "-o <file> writes ~512 KB energies (exercises POSIX write); without it no data file; point it at the session Lustre dataset/",
        "deck": "data/bm1 (65 536 poses) / data/bm2 via --deck <dir>; must be the annotated tree's copy for the annotated binary",
    },
    "trace_expectation": {
        "measured": "2 nodes x 1 process, HIP, -i 5000, dftracer with HIP + PAPI + variorum + hwloc; 122 362 app + 39 010 service events",
        "per_rank": {"CPP_APP": "14 (only after fixing both traps)", "KERNEL_DISPATCH": "~5 000 (= -i + 2, + ~3 rocclr copy kernels)",
                     "HIP_RUNTIME_API": "~10 000 (2 per launch)", "MEMORY_COPY": "6 (5 H2D + 1 D2H)", "SCRATCH_MEMORY": "1",
                     "PAGE_MIGRATION": "0 (expected: explicit hipMalloc)", "papi": "~670 (one per DFTRACER_PAPI_SAMPLE_INTERVAL_MS)",
                     "POSIX": "~1 350 (ROCm/hwloc sysfs probing + the -o write)",
                     "STDIO": "~38 500 (ROCm runtime fopen/fgets/fclose on sysfs, NOT the app)", "MPI": "0 (expected)", "HDF5": "0 (expected)"},
        "node_level": "dftracer_service per node (type 7 + type 13): sys (cpu/mem), io (block devices), net (NICs), gpu/power (variorum socket_<n>.GPU_<n> watts)",
    },
    "variants": {},
    "notes": [
        "extra_cmake_flags cannot carry a multi-token -D value: a space splits it (CMake Error: Unknown argument -I...), a ';' truncates the command",
        "session_build_annotated needs build_subdir=\"source\" for annotated/source/ (else 'does not appear to contain CMakeLists.txt')",
        "clang_syntax_check is useless here (hardcoded g++ -std=c++14, no -D): its errors are not annotation defects; "
        "session_build_annotated is the authoritative check; clang_lint_annotations works and should still be run",
        "STDIO dwarfing everything is ROCm init sysfs enumeration, not a miniBUDE I/O bottleneck",
    ],
}

RULES = [
    {"id": "build_type_release", "require": r"-DCMAKE_BUILD_TYPE=(?:Release|Debug)\b", "when": r"\bcmake\b.*-S|extra_cmake_flags|-DMODEL=",
     "why": "CMakeLists.txt: FATAL_ERROR 'Only Release or Debug is supported'; the session tools default to RelWithDebInfo",
     "fix": "pass -DCMAKE_BUILD_TYPE=Release in every configure / extra_cmake_flags"},
    {"id": "no_relwithdebinfo", "forbid": r"-DCMAKE_BUILD_TYPE=(?!Release\b|Debug\b)\w+",
     "why": "only Release or Debug is supported", "fix": "-DCMAKE_BUILD_TYPE=Release"},
    {"id": "offload_arch", "require": r"--offload-arch=gfx942", "when": r"-DMODEL=hip",
     "why": "the HIP model sets no offload arch; hipcc guesses from the (GPU-less) build host",
     "fix": "-DCXX_EXTRA_FLAGS=--offload-arch=gfx942"},
    {"id": "single_token_d", "forbid": r"-D\w+=\"[^\"]*\s[^\"]*\"|-D\w+='[^']*\s[^']*'|-D\w+=[^\s;]*;",
     "why": "extra_cmake_flags cannot carry a multi-token -D value (space splits: 'Unknown argument -I...'; ';' truncates the command)",
     "fix": "one token per -D: include in CMAKE_CXX_FLAGS, lib in CXX_EXTRA_LIBRARIES, rpath in CMAKE_EXE_LINKER_FLAGS"},
    {"id": "no_prefix_path", "forbid": r"-DCMAKE_PREFIX_PATH=.*dftracer",
     "why": "miniBUDE has no find_package: CMAKE_PREFIX_PATH does nothing",
     "fix": "-DCMAKE_CXX_FLAGS=-I<dftracer>/include -DCXX_EXTRA_LIBRARIES=<dftracer>/lib64/libdftracer_core.so -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath,<dftracer>/lib64"},
    {"id": "no_install_bin", "forbid": r"install_ann/bin/",
     "why": "cmake --install strips the rpath", "fix": "run the binary from build_ann/ (or re-add LD_LIBRARY_PATH)"},
    {"id": "no_mpi_launch", "forbid": r"\b(?:mpirun|mpiexec)\b",
     "why": "miniBUDE is not MPI: multi-node means independent single-process instances", "fix": "launch one process per instance"},
    {"id": "deck_given", "require": r"--deck\s+\S+", "when": r"\bbude\b",
     "why": "the run needs the pose deck (data/bm1 or data/bm2, the annotated tree's copy for the annotated binary)",
     "fix": "--deck <tree>/data/bm1"},
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
    def workload_minibude_recipe(variant: str = "") -> dict:
        """Predictor: the miniBUDE HIP/MI300A build/annotate/run recipe dftracer-agents verified (Release-only build type,
        --offload-arch=gfx942, single-token dftracer link flags, the two annotation traps, run sizing -i/-p/-w/-o/--deck,
        expected trace categories) as structured JSON. Use before building, annotating or tracing miniBUDE. variant:
        optional (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_minibude_check(commands: list) -> dict:
        """Validator: check a proposed miniBUDE recipe or command list against the skill's rules (CMAKE_BUILD_TYPE Release or
        Debug only, gfx942 offload arch for MODEL=hip, single-token -D values, no CMAKE_PREFIX_PATH, no install_ann/bin,
        no MPI launcher, --deck given). commands: list of shell lines (or a newline-separated string / JSON text). Returns
        {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
