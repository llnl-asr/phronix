"""workload_rajaperf: the RAJAPerf (LLNL/RAJAPerf, CMake+BLT compute-kernel benchmark suite, HIP/MPI/OpenMP variants) build,
dftracer link, annotation scope and run recipe dftracer-agents' workload-rajaperf skill verified on Tuolumne MI300A, as
structured data (predictor), and a deterministic check of a proposed recipe or command list against that skill's rules,
including --kernels/--variants names against the suite's real lists (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_rajaperf"

KERNELS = (
    "Basic_ARRAY_OF_PTRS Basic_COPY8 Basic_DAXPY Basic_DAXPY_ATOMIC Basic_EMPTY Basic_IF_QUAD Basic_INDEXLIST "
    "Basic_INDEXLIST_3LOOP Basic_INIT3 Basic_INIT_VIEW1D Basic_INIT_VIEW1D_OFFSET Basic_MAT_MAT_SHARED Basic_MULADDSUB "
    "Basic_NESTED_INIT Basic_PI_ATOMIC Basic_PI_REDUCE Basic_REDUCE3_INT Basic_REDUCE_STRUCT Basic_TRAP_INT Basic_MULTI_REDUCE "
    "Lcals_DIFF_PREDICT Lcals_EOS Lcals_FIRST_DIFF Lcals_FIRST_MIN Lcals_FIRST_SUM Lcals_GEN_LIN_RECUR Lcals_HYDRO_1D "
    "Lcals_HYDRO_2D Lcals_INT_PREDICT Lcals_PLANCKIAN Lcals_TRIDIAG_ELIM Polybench_2MM Polybench_3MM Polybench_ADI "
    "Polybench_ATAX Polybench_FDTD_2D Polybench_FLOYD_WARSHALL Polybench_GEMM Polybench_GEMVER Polybench_GESUMMV "
    "Polybench_HEAT_3D Polybench_JACOBI_1D Polybench_JACOBI_2D Polybench_MVT Stream_ADD Stream_COPY Stream_DOT Stream_MUL "
    "Stream_TRIAD Apps_CONVECTION3DPA Apps_DEL_DOT_VEC_2D Apps_DIFFUSION3DPA Apps_EDGE3D Apps_ENERGY Apps_FEMSWEEP Apps_FIR "
    "Apps_INTSC_HEXHEX Apps_INTSC_HEXRECT Apps_LTIMES Apps_LTIMES_NOVIEW Apps_MASS3DEA Apps_MASS3DPA Apps_MASS3DPA_ATOMIC "
    "Apps_MASSVEC3DPA Apps_MATVEC_3D_STENCIL Apps_NODAL_ACCUMULATION_3D Apps_PRESSURE Apps_VOL3D Apps_ZONAL_ACCUMULATION_3D "
    "Algorithm_SCAN Algorithm_SORT Algorithm_SORTPAIRS Algorithm_REDUCE_SUM Algorithm_MEMSET Algorithm_MEMCPY Algorithm_ATOMIC "
    "Algorithm_HISTOGRAM Comm_HALO_PACKING Comm_HALO_PACKING_FUSED Comm_HALO_SENDRECV Comm_HALO_EXCHANGE Comm_HALO_EXCHANGE_FUSED"
).split()
VARIANTS = ("Base_Seq Lambda_Seq RAJA_Seq Base_OpenMP Lambda_OpenMP RAJA_OpenMP Base_OpenMPTarget RAJA_OpenMPTarget Base_CUDA "
            "Lambda_CUDA RAJA_CUDA Base_HIP Lambda_HIP RAJA_HIP Kokkos_Lambda Base_SYCL RAJA_SYCL").split()

RECIPE = {
    "app": "RAJAPerf",
    "repo": "https://github.com/LLNL/RAJAPerf",
    "what": "loop/kernel compute benchmark suite (60+ micro-kernels); no file I/O in its core kernels",
    "build_system": "cmake + BLT",
    "systems": ["tuolumne"],
    "configure": [
        "cmake -S <src> -B <build> -DENABLE_HIP=ON -DENABLE_MPI=ON -DRAJA_PERFSUITE_ENABLE_MPI=ON -DENABLE_OPENMP=ON -DENABLE_TESTS=ON "
        "\"-DCMAKE_PREFIX_PATH=/opt/rocm-7.2.1;<dftracer prefix: <venv>/lib/python3.13/site-packages/dftracer>\" "
        "-DRAJA_ENABLE_EXTERNAL_ROCPRIM=ON -Drocprim_DIR=/opt/rocm-7.2.1/lib/cmake/rocprim",
    ],
    "cmake_notes": [
        "-DENABLE_HIP=ON is a BLT option (genuine app GPU usage)",
        "-DRAJA_PERFSUITE_ENABLE_MPI=ON alone leaves MPI OFF (RAJA_PERFSUITE_NUM_MPI_TASKS: 0): also pass -DENABLE_MPI=ON",
        "RAJA_PERFSUITE_GPU_BLOCKSIZES=\"\" compiles exactly ONE tuning (block_256; plus blkatm_direct_256/blkatm_occgs_256 for Stream_DOT)",
    ],
    "dftracer_link": [
        "# top-level CMakeLists.txt, right after set(RAJA_PERFSUITE_DEPENDS RAJA):",
        "find_package(rocprofiler-sdk CONFIG REQUIRED)   # BEFORE find_package(dftracer): dftracer-targets.cmake references rocprofiler-sdk::rocprofiler-sdk",
        "find_package(dftracer REQUIRED)",
        "list(APPEND RAJA_PERFSUITE_DEPENDS dftracer)     # plain dftracer target; dftracer::dftracer does not exist",
    ],
    "annotation": {
        "annotate": {"src/RAJAPerfSuiteDriver.cpp": "main() (only entry point; owns MPI_Init/MPI_Finalize; constructs Executor)",
                     "src/common/Executor.cpp": "Executor::runSuite(), Executor::runKernel() (comp=comm: MPI_Comm_size + Allreduce checksum)",
                     "src/common/KernelBase.cpp": "KernelBase::execute(), KernelBase::runKernel() (the shared function-pointer dispatch)"},
        "never": "kernel files under src/<Category>/*.cpp (basic, lcals, polybench, stream, apps, comm, algorithm), incl. runHipVariant()",
        "no_shared_hip_helper": "grep -rn runHipVariant src/common/ returns nothing: annotate KernelBase::runKernel() only",
        "main": ["DFTRACER_CPP_INIT() as the very first statement of main() (before MPI_Init, unconditional, not inside #if RAJA_PERFSUITE_ENABLE_MPI)",
                 "DFTRACER_CPP_REGION_START(main);  DFTRACER_CPP_REGION_DYN_UPDATE(main, \"comp\", \"cpu\");",
                 "...", "DFTRACER_CPP_REGION_END(main);  DFTRACER_CPP_FINI();  return 0;"],
        "method_body": "DFTRACER_CPP_FUNCTION(); DFTRACER_CPP_FUNCTION_UPDATE(\"comp\", ...); after the opening brace",
        "verify": "grep -n \"DFTRACER_CPP_FUNCTION\\|DFTRACER_CPP_REGION\\|DFTRACER_CPP_INIT\\|DFTRACER_CPP_FINI\" <file>",
    },
    "run": {
        "command": "flux run -N 4 -n 16 --exclusive <build>/bin/raja-perf.exe --kernels <Group_Name ...> --variants <Variant ...> --outdir <dir>",
        "verify_ran": ["runSuite() span not microsecond-scale", "KERNEL_DISPATCH / HIP_RUNTIME_API counts non-zero",
                       "<outdir>/<outfile>-timing-<combiner>.csv present", "16 distinct PIDs, 4 distinct hostnames",
                       "'Checksum Report for 16 MPI ranks'", "data-space echo (Hip - HipDevice) in the log"],
        "timing_source": "<outdir>/RAJAPerf-timing-Average.csv and RAJAPerf-kernel-run-data.csv (untraced), not the trace buckets",
        "replicates": ">= 5, interleaved arms, serial (never two timing drivers on one allocation)",
    },
    "kernels": KERNELS,
    "variants_list": VARIANTS,
    "variants": {},
    "notes": [
        "I/O dimension structurally not applicable (STDIO/POSIX ~77% ROCm/hwloc /proc+/sys probing); only lever HWLOC_XMLFILE (<1%)",
        "MPI_Barrier (~8.5%/rank) is the timing harness in KernelBase::startTimer/stopTimer: never reduce it; real comm is halo p2p (MPI_Waitany ~2.7%/rank)",
        "GPU-launch-overhead-bound by design (RepCount auto-scaling); HIP graphs is the only physically valid compute lever (<= 2.1%)",
        "measured no-ops/regressions: Release -O3 (+1.0%), RAJA_PERFSUITE_TUNING_HIP_ARCH=942 (0.0%), HSA_ENABLE_INTERRUPT=0 (+3.78%), --hip-data-space HipManaged (-2.9% wall)",
        "legitimate comm lever: --hip-mpi-data-space HipDevice with MPICH_GPU_SUPPORT_ENABLED=1 (no semantic change)",
        "clang_syntax_check fails on every file (RAJA/config.hpp not found): defer to the full CMake build",
        "session_annotation_report reports 0% on RAII C++ macros: ground-truth with grep",
    ],
}

RULES = [
    {"id": "enable_mpi_both", "require": r"-DENABLE_MPI=ON", "when": r"-DRAJA_PERFSUITE_ENABLE_MPI=ON",
     "why": "RAJA_PERFSUITE_ENABLE_MPI is a cmake_dependent_option on BLT's ENABLE_MPI: alone it leaves MPI silently OFF",
     "fix": "pass -DENABLE_MPI=ON as well"},
    {"id": "dftracer_target", "forbid": r"dftracer::dftracer\b",
     "why": "dftracer::dftracer does not exist for this build", "fix": "link the plain dftracer target (list(APPEND RAJA_PERFSUITE_DEPENDS dftracer))"},
    {"id": "rocprofiler_found", "require": r"find_package\(\s*rocprofiler-sdk", "when": r"find_package\(\s*dftracer",
     "why": "dftracer-targets.cmake references rocprofiler-sdk::rocprofiler-sdk without resolving it", "fix": "find_package(rocprofiler-sdk CONFIG REQUIRED) before find_package(dftracer)"},
    {"id": "no_hipmanaged", "forbid": r"--hip-data-space\s+HipManaged",
     "why": "measured REGRESSION at 4 nodes/16 ranks: wall 75.61 -> 77.81 s, timed sum -3.6% (fine-grained coherent memory)", "fix": "keep the default HipDevice"},
    {"id": "no_hostadvisefine", "forbid": r"--hip-data-space\s+HipHostAdviseFine",
     "why": "hard SIGABRT rc=134 'Memory access fault by GPU node-N' on ROCm 7.2.1", "fix": "do not use it"},
    {"id": "no_gpu_block_size_ab", "forbid": r"--gpu_block_size",
     "why": "at runtime it SKIPS kernels that do not support the option, changing the work executed", "fix": "rebuild with RAJA_PERFSUITE_GPU_BLOCKSIZES instead"},
    {"id": "no_hsa_interrupt_0", "forbid": r"HSA_ENABLE_INTERRUPT=0",
     "why": "+3.78% REGRESSION: busy-poll steals host cores from Base_Seq", "fix": "drop it"},
    {"id": "region_bare_identifier", "forbid": r"DFTRACER_CPP_REGION_(?:START|END|DYN_UPDATE)\(\s*\"",
     "why": "dftracer.h token-pastes profiler_##name: 'pasting formed profiler_\"main\", an invalid preprocessing token' at final link",
     "fix": "DFTRACER_CPP_REGION_START(main); / DFTRACER_CPP_REGION_DYN_UPDATE(main, \"comp\", \"cpu\"); / DFTRACER_CPP_REGION_END(main);"},
    {"id": "no_c_init", "forbid": r"DFTRACER_C_INIT\b",
     "why": "RAJAPerf is C++: the C init macro is wrong (CP1)", "fix": "DFTRACER_CPP_INIT() as the first statement of main()"},
    {"id": "exclusive_multinode", "require": r"--exclusive", "when": r"flux\s+run\b.*-N\s*[2-9]",
     "why": "a 4-rank run silently masquerades as 4-node (flux run -N4 -n4)", "fix": "flux run -N 4 -n 16 --exclusive and verify 16 PIDs / 4 hosts"},
    {"id": "no_concurrent_drivers", "forbid": r"raja-perf\.exe\b[^&]*&\s*$",
     "why": "two timing drivers on one allocation inflated 71 s -> 147 s -> 304 s", "fix": "serialize runs; interleave arms"},
    {"id": "no_kernel_annotation", "forbid": r"clang_annotate\w*.*src/(?:basic|lcals|polybench|stream|apps|comm|algorithm)/",
     "why": "kernel files put dftracer macros inside the per-iteration hot loop (CP10)", "fix": "annotate only the driver, Executor and KernelBase"},
]


def _names(c, flag):
    m = re.search(flag + r"((?:\s+(?!-)\S+)+)", c)
    return m.group(1).split() if m else []


def _extra(commands):
    out = []
    for c in _commands(commands):
        if "--kernels" in c:
            bad = [k for k in _names(c, r"--kernels") if k not in KERNELS]
            out.append({"check": "kernels_full_names", "ok": not bad,
                        "detail": "ok" if not bad else f"not a <Group>_<Name> kernel: {bad} (an unmatched name silently runs ZERO kernels)",
                        "fix": "" if not bad else "use full names from --print-kernels, e.g. Basic_DAXPY, Stream_DOT"})
            if "--variants" not in c:
                out.append({"check": "variants_given", "ok": False, "detail": "--kernels without --variants",
                            "fix": "pass --variants (e.g. Base_Seq Base_HIP)"})
        if "--variants" in c:
            bad = [v for v in _names(c, r"--variants") if v not in VARIANTS]
            out.append({"check": "variants_valid", "ok": not bad, "detail": "ok" if not bad else f"unknown variants {bad}",
                        "fix": "" if not bad else "use names from --print-variants"})
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
    def workload_rajaperf_recipe(variant: str = "") -> dict:
        """Predictor: the RAJAPerf recipe dftracer-agents verified on Tuolumne (ROCm 7.2.1): CMake flags (ENABLE_HIP, ENABLE_MPI +
        RAJA_PERFSUITE_ENABLE_MPI, rocprim), the dftracer find_package/link snippet, the annotation scope (driver main, Executor,
        KernelBase) and main() macro layout, the multi-node run and its verification list, the full kernel and variant lists,
        and measured no-op/regression levers. variant: optional (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_rajaperf_check(commands: list) -> dict:
        """Validator: check a proposed RAJAPerf recipe, CMake snippet or command list against the skill's rules: ENABLE_MPI with
        RAJA_PERFSUITE_ENABLE_MPI, plain dftracer target after find_package(rocprofiler-sdk), no HipManaged/HipHostAdviseFine,
        no --gpu_block_size or HSA_ENABLE_INTERRUPT=0, bare-identifier REGION macros, no C init, --exclusive multi-node runs,
        no concurrent drivers, no kernel-file annotation, and every --kernels/--variants name valid. commands: list of lines (or
        newline/JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _extra(commands)
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res
