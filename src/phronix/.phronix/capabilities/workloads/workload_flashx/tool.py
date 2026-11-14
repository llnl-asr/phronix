"""workload_flashx: the Flash-X (Fortran/C/C++ multiphysics AMR code, Python setup script + GNU Make) Sedov 3D build/annotate/run
recipe that dftracer-agents' workload-flashx skill verified on Tuolumne (source HDF5, GNU 11.2 MPI wrappers, +parallelIO,
Paramesh AMR production sizing, flux proxy wrapper pattern, measured I/O optimization ladder), as structured data (predictor),
and a deterministic check of a proposed recipe or command list against that skill's rules (validator). Nothing here runs."""
import json
import re

CAP = "workload_flashx"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "Flash-X",
    "repo": "git@github.com:Flash-X/Flash-X.git",
    "build_system": "Flash-X Python ./setup script generating object/ + GNU Make (NOT cmake/autotools/pip; session_configure fails)",
    "languages": ["Fortran (~2600 .F90)", "C (126)", "C++ (6)", "Python (70)"],
    "systems": ["tuolumne"],
    "compilers": "GNU 11.2 Cray MPICH wrappers /opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/{mpif90,mpicc,mpicxx} (Cray ftn/craycc fail)",
    "makefile_h": {
        "file": "sites/Prototypes/Linux/Makefile.h (and object/Makefile.h after setup)",
        "MPI_PATH": "/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2",
        "HDF5_PATH": "<WS>/hdf5_1.14 (BUILT/installed prefix, never the source unpack dir or the Cray/system module)",
        "FFLAGS": "+= -fallow-argument-mismatch",
    },
    "dependencies": {
        "hdf5": [
            "curl -fkL https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.3/src/hdf5-1.14.3.tar.gz -o hdf5-1.14.3.tar.gz   # 1.14.5 also used",
            "CC=mpicc ./configure --prefix=<WS>/hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production && make -j8 && make install",
            "sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' <WS>/hdf5_1.14/include/H5Apublic.h",
            "test -d $HDF5_PATH/lib && ls $HDF5_PATH/lib/libhdf5.so*   # before setup",
        ],
    },
    "build": [
        "git submodule update --init --recursive   # PARAMESH must be initialized before setup",
        "HDF5_PATH=<WS>/hdf5_1.14 bash setup Sedov -auto -3d +parallelIO   # -auto alone selects SERIAL HDF5 IO (rank 0 writes everything)",
        "edit object/Makefile.h (HDF5_PATH, MPI_PATH, FFLAGS -fallow-argument-mismatch) AFTER setup (setup wipes object/)",
        "recreate object/dftracer_init_fini.c shim + MACHOBJ += dftracer_init_fini.o AFTER setup (annotated build)",
        "cd object && make -j   # exe object/flashx",
        "ldd object/flashx | grep hdf5   # must be <WS>/hdf5_1.14/lib/libhdf5.so.310, never /lib64/libhdf5.so.103",
        "grep IO/IOMain object/Units   # hdf5/parallel/PM expected",
    ],
    "annotate": [
        "FUNCTION mode; auto-annotate the C/C++ IO layer (66 C IO files) with clang tools",
        "Fortran entry (program Flashx in source/Simulation/main.F90) has no C main: object/dftracer_init_fini.c with __attribute__((constructor)) calling DFTRACER_C_INIT and __attribute__((destructor)) calling DFTRACER_C_FINI, added to ALL_OBJ_FILES / MACHOBJ",
        "if FUNCTION mode yields no traces (crayftn may not fire ctor/dtor): pivot to PRELOAD (DFTRACER_INIT=PRELOAD, DFTRACER_DATA_DIR=all, LD_PRELOAD=<dft lib64>/libdftracer_preload.so)",
        "low coverage: manually annotate source/IO/IOMain/** with dftracer's Fortran API",
    ],
    "run_env": {
        "LD_LIBRARY_PATH": "<WS>/hdf5_1.14/lib:<dftracer lib64>:/opt/cray/pe/cce/20.0.0/cce/x86_64/lib:/usr/lib64:$LD_LIBRARY_PATH",
        "DFTRACER_ENABLE": "1", "DFTRACER_INIT": "PRELOAD or FUNCTION", "DFTRACER_DATA_DIR": "all", "DFTRACER_INC_METADATA": "1",
        "DFTRACER_LOG_FILE": "<WS>/traces/raw/<run> (workspace, NOT the Lustre output dir)",
        "MPICH_GPU_SUPPORT_ENABLED": "0", "HDF5_USE_FILE_LOCKING": "FALSE",
    },
    "run": [
        "write production_run.sh exporting ALL env vars (no module load inside), cd object/, ./flashx (no argv; it reads ./flash.par)",
        "flux proxy <alloc_id> flux run -N <nnodes> -n $((<nnodes> * 48)) --exclusive ./production_run.sh",
        "single node without proxy: flux run -N 1 -n 4 -x DFTRACER_ENABLE -x DFTRACER_INIT -x LD_PRELOAD ./flashx",
        "ds -> <lustre>/$USER/flashx symlink in the RUN cwd (object/) for the 80-column flash.par output path",
    ],
    "variants": {
        "smoke": {"grid": "16^3", "ranks": 1, "runtime": "< 5 s", "io": "< 1 MB", "result": "annotated: 6566 events (HDF5 5236, POSIX 696, C_APP 552, dftracer 43, STDIO 36, MPI 3)"},
        "production_384": {"flash.par": {"nblockx": 9, "nblocky": 9, "nblockz": 9, "iProcs": 1, "jProcs": 1, "kProcs": 1,
                                         "lrefine_max": 6, "lrefine_min": 4, "sim_rInit": 0.013671875,
                                         "checkpointFileIntervalTime": 0.03, "tmax": 0.5, "nend": 1000000,
                                         "wall_clock_time_limit": 3600, "useCollectiveHDF5": ".true."},
                           "ranks": "384 (8 nodes x 48)", "expect": ">= 500 MB per checkpoint, >= 50 steps in 5 min, >= 30 min runtime",
                           "wall": "request >= 60 min"},
        "io_opt3": {"setup": "+parallelIO", "env": {"MPICH_MPIIO_HINTS": "*:romio_cb_write=enable:cb_nodes=16", "CRAY_CB_NODES_MULTIPLIER": "2"},
                    "lustre": "16 x 4 MB stripes", "result": "critical-path write 11.09 s -> 1.45 s (7.6x), 16 aggregators, top-1 share 91% -> 6.8%"},
    },
    "notes": [
        "verify NXB from the build log (grep -E 'NXB|NYB|NZB'), not the Makefile",
        "keep flash.par pure ASCII and lines < 80 columns; grep the run log for 'syntax error'",
        "Sedov 3D I/O hot spots: io_h5write_unknowns_ 32%, xfer pipeline 26.6%, io_h5_attribute_create 9.6%",
        "search papers for production configs first (session_search_papers_for_config app_name=Flash-X problem_name=Sedov; Jain et al. 2021 arXiv:2103.04267)",
        "ask the user for the active allocation; use ALL its nodes; verify with flux jobs",
    ],
}

# rule kinds: forbid (regex must not match any command), require (regex must match some command; only when `when` matches, if given)
RULES = [
    {"id": "gnu_wrappers_not_cray", "forbid": r"(?:^|[\s=/])(?:ftn|craycc|crayftn)(?:\s|$)",
     "why": "Cray PE ftn/craycc failed to build Flash-X (Fortran flag incompatibilities) (2026-07-08)",
     "fix": "use /opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/{mpif90,mpicc,mpicxx}, MPI_PATH=/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2"},
    {"id": "fallow_argument_mismatch", "require": r"-fallow-argument-mismatch", "when": r"\bFFLAGS\b",
     "why": "gfortran strict checking vs MPI Fortran module interfaces fails the build", "fix": "add -fallow-argument-mismatch to FFLAGS"},
    {"id": "hdf5_path_built_prefix", "forbid": r"HDF5_PATH=\S*hdf5-1\.\d+\.\d+(?:/|\s|$)|HDF5_PATH=/usr\b",
     "why": "a source-only (hyphenated unpack) dir or the system HDF5 silently falls back to /lib64/libhdf5.so.103 (HDF5 1.10.5)",
     "fix": "HDF5_PATH=<WS>/hdf5_1.14 (built/installed prefix); check ldd flashx | grep hdf5"},
    {"id": "parallel_io_for_collective", "require": r"\+parallelIO", "when": r"useCollectiveHDF5\s*=\s*\.true\.",
     "why": "-auto selects the serial HDF5 IO unit (HDF5_MODE hardcoded independent): useCollectiveHDF5 is inert, rank 0 writes ~91% of bytes",
     "fix": "bash setup Sedov -auto -3d +parallelIO, then re-apply Makefile.h and the dftracer shim"},
    {"id": "no_par_argv", "forbid": r"\bflashx\s+\S+\.par\b",
     "why": "flashx ignores a par-file argument and always reads ./flash.par (a production launch re-ran the smoke config)",
     "fix": "copy/symlink the config to object/flash.par; run ./flashx with no argument"},
    {"id": "no_env_through_proxy", "forbid": r"flux\s+proxy\s+\S+\s+flux\s+run\b.*(?:\s-x\s|--env)",
     "why": "env vars are not forwarded through flux proxy (and --env with ;/:/* drops the binary)",
     "fix": "export everything inside production_run.sh and run: flux proxy <alloc> flux run -N <n> -n <n*48> --exclusive ./production_run.sh"},
    {"id": "no_module_load_under_proxy", "forbid": r"flux\s+proxy.*module\s+load|module\s+load.*flux\s+proxy",
     "why": "Lmod re-loading modules inside a flux proxy job deadlocks (768 bash procs stuck on lmod shell load cray-mpich/9.0.1)",
     "fix": "do not load modules in the run script; the allocation already has them"},
    {"id": "paramesh_amr_procs", "forbid": r"\b[ijk]Procs\s*=\s*(?:[2-9]|\d{2,})",
     "why": "uniform-grid mode (iProcs>1, default nblockx/y/z=1) gives ~140 KB checkpoints and short runtime",
     "fix": "Paramesh AMR: iProcs=jProcs=kProcs=1 with nblockx/y/z=9"},
    {"id": "flash_par_ascii", "forbid": r"^\s*\w+\s*=.*[^\x00-\x7f]",
     "why": "a non-ASCII char (e.g. an em-dash) makes the parser skip the line: 'read : skipping the following line due to a syntax error'",
     "fix": "keep flash.par pure ASCII"},
    {"id": "traces_in_workspace", "forbid": r"DFTRACER_LOG_FILE=\S*(?:lustre|/ds/)",
     "why": "traces must land in <WS>/traces/, not the Lustre output dir", "fix": "DFTRACER_LOG_FILE=<WS>/traces/raw/<run>"},
    {"id": "no_pip_configure", "forbid": r"pip\s+install\s+-e\s+\S*[Ff]lash",
     "why": "Flash-X has no setup.py/pyproject.toml; session_configure's pip install -e fails",
     "fix": "git submodule update --init --recursive; bash setup Sedov -auto -3d +parallelIO; make in object/"},
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
    def workload_flashx_recipe(variant: str = "") -> dict:
        """Predictor: the Flash-X Sedov 3D recipe dftracer-agents verified on Tuolumne (submodules, setup +parallelIO, Makefile.h
        with GNU 11.2 MPI wrappers and source-built HDF5, -fallow-argument-mismatch, init/fini shim, PRELOAD fallback, run env,
        flux proxy wrapper script) as structured JSON. variant: optional, one of smoke, production_384 (validated flash.par),
        io_opt3 (measured best I/O config). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_flashx_check(commands: list) -> dict:
        """Validator: check a proposed Flash-X recipe, flash.par lines or command list against the skill's rules (no Cray ftn/craycc,
        -fallow-argument-mismatch, HDF5_PATH at a built prefix, +parallelIO when useCollectiveHDF5, no par argv, no env/-x or
        module load through flux proxy, Paramesh AMR procs=1, ASCII flash.par, traces in the workspace, no pip install -e).
        commands: list of lines (or one newline-separated string / JSON text). Returns {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
