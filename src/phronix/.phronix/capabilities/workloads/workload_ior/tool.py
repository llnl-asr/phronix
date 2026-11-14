"""workload_ior: the IOR 4.0.0 (LLNL parallel I/O benchmark, Autotools, C) build/annotate/run recipe that dftracer-agents'
workload-ior skill verified on Tuolumne (POSIX/MPI-IO/HDF5 backends, VAST and Lustre ROMIO findings), as structured data
(predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator).
Nothing here runs a build or a job."""
import json
import re

CAP = "workload_ior"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "IOR",
    "version": "4.0.0 (https://github.com/llnl/ior, tag 4.0.0)",
    "build_system": "autotools (no pre-generated configure)",
    "languages": ["C"],
    "systems": ["tuolumne"],
    "modules": ["cray-mpich/9.0.1", "unload cray-hdf5-parallel before building dftracer with HDF5"],
    "env": {
        "LD_LIBRARY_PATH (annotated runs)": "<dftracer_lib64>:<python-3.13.2 module lib>:$LD_LIBRARY_PATH (python module libstdc++ has GLIBCXX_3.4.29 and must precede /usr/lib64)",
    },
    "bootstrap": ["cd <source> && touch NEWS AUTHORS && autoreconf -fi -I config"],
    "configure": [
        "CFLAGS=\"-g -O2 -Wno-incompatible-function-pointer-types -fcommon\" LDFLAGS=\"-fuse-ld=bfd\" ./configure --without-hdf5 --without-ncmpi --prefix=<install>",
        "make clean && make -j8",
    ],
    "configure_hdf5": [
        "make distclean; rm -rf .deps src/.deps autom4te.cache config.status config.log Makefile",
        "export CPPFLAGS=\"-I${HDF5_PREFIX}/include\" LDFLAGS=\"-L${HDF5_PREFIX}/lib -Wl,-rpath,${HDF5_PREFIX}/lib\" LIBS=\"-lhdf5 -lz\"",
        "./configure --with-hdf5=yes --prefix=<install>",
        "grep USE_HDF5_AIORI config.h   # must show 1 (config.log: USE_HDF5_AIORI_TRUE='' means enabled, '#' disabled)",
    ],
    "annotated_build": [
        "cd <ws>/annotated/source && autoconf --version   # only if older than configure.ac's AC_PREREQ: sed -i 's/AC_PREREQ(\\[2.71\\])/AC_PREREQ([2.69])/' configure.ac",
        "autoreconf -fi -I config   # the annotated tree regenerates its OWN build system; never copy configure/Makefile.in from source/",
        "CFLAGS=\"-g -O2 -Wno-incompatible-function-pointer-types -fcommon -I<dftracer_inc>\" "
        "LDFLAGS=\"-fuse-ld=bfd -L<dftracer_lib64> -Wl,-rpath,<dftracer_lib64> -Wl,--allow-shlib-undefined -Wl,--no-as-needed\" "
        "LIBS=\"-ldftracer_core -lstdc++\" <ws>/annotated/configure --prefix=<ws>/install_ann",
        "make -C src -j8 install   # build src/ only; contrib/cbif.c fails on open64/lseek64 under cce (unrelated)",
    ],
    "dftracer_install_tuolumne": [
        "HDF5_SRC=/opt/cray/pe/hdf5-parallel/1.14.3.7/crayclang/20.0; P=<ws>/tmp/hdf5_patched",
        "cp -r \"$HDF5_SRC/include\" \"$P/include\"; ln -s \"$HDF5_SRC/lib\" \"$P/lib\"; chmod -R u+w \"$P/include\"",
        "sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' \"$P/include/H5Apublic.h\"",
        "module unload cray-hdf5-parallel",
        "export DFTRACER_ENABLE_MPI=ON DFTRACER_ENABLE_HDF5=ON DFTRACER_ENABLE_FTRACING=ON DFTRACER_ENABLE_HIP_TRACING=OFF DFTRACER_DISABLE_HWLOC=ON",
        "export MPI_C_COMPILER=$(which mpicc) MPI_CXX_COMPILER=$(which mpicxx) HDF5_ROOT=$P HDF5_DIR=$P",
        "pip install --no-cache-dir --force-reinstall --no-deps -v \"git+https://github.com/llnl-asr/dftracer.git@develop\"",
        "grep -E \"DFTRACER_(MPI|HDF5|FTRACING)_ENABLE\" <venv>/.../dftracer/include/dftracer/core/dftracer_config.hpp   # all three == 1",
    ],
    "annotate": [
        "DFTRACER_C_INIT(NULL, NULL, NULL) after MPI_Init; DFTRACER_C_FINI() AFTER ior_main(), before MPI_Finalize",
        "clang_annotate_project init_args=\"NULL, NULL, NULL\" (never -1: process_id is int *)",
        "add braces to braceless if (dryRun) return NULL; before inserting END",
        "annotate only the HDF5_Create definition (grep -n HDF5_Create file.c | grep -v ';$')",
        "post-pass: remove duplicate END() before HDF5_CHECK/MPI_CHECK macros (aiori-HDF5.c); one END before the real return",
        "post-pass: grep every file for return-then-END dead code and END spliced into WARNF/ERRF/INFOF",
        "utilities.c: clang_extract_functions returns 0 functions; annotate SetHints, ReadStoneWallingIterations, StoreStoneWallingIterations, aligned_buffer_alloc/free, GetNumTasks* via clang_insert_line",
    ],
    "smoke": [
        "./src/ior -a POSIX -b 1m -t 1m -s 1 -F -C -o /tmp/ior_smoke_test",
        "container (OpenMPI as root): OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 mpirun -np 1 --allow-run-as-root ./src/ior -a POSIX -b 1m -t 1m -s 1 -F -C -o /tmp/ior_smoke_test",
    ],
    "trace": [
        "DFTRACER_DATA_DIR=all; with a run_id containing '/', traces land in <ws>/traces/<app>/: cp <ws>/traces/ior/*.pfw.gz <ws>/traces/ before session_split_traces",
        "service: DFTRACER_ENABLE=1 DFTRACER_LOG_FILE=<ws>/traces/<RUN_ID> DFTRACER_DATA_DIR=all DFTRACER_TRACE_INTERVAL_MS=1000 <install_ann>/bin/dftracer_service start <ws>/traces/service ... stop <ws>/traces/service",
    ],
    "analyze": [
        "mcp analyze: cluster_type=local cluster_n_workers=1 (more workers race on .dftindex and under-count); wipe stale .dftindex and checkpoint/ first; never pass cluster_cores",
        "checkpoint mode is authoritative (non-checkpoint mode double counts)",
        "run dfanalyzer inside a flux allocation (1 node is enough) with DEFAULT worker sizing; login node + explicit n_workers -> DFTUtilsError: Resource temporarily unavailable",
        "cross-check raw_stats_summary unique_file_count/unique_process_count against files on disk",
        "mcp diagnose errors 'Diagnoser' object has no attribute 'diagnose_checkpoint': read checkpoint/_flat_view_*.parquet + _raw_stats_*.json",
    ],
    "variants": {
        "vast_hdf5_romio_opt": {"filesystem": "VAST NVMe", "scale": "192 ranks, 2 nodes",
                                "env": {"MPICH_MPIIO_HINTS": "*:romio_cb_write=enable"},
                                "ior_flags": "-a HDF5 -b 64m -t 16m -s 4 -c -Y",
                                "result": "total 168.8s -> 112.9s (-33%), write 352 -> 557 MiB/s, read 1705 -> 1991 MiB/s, POSIX calls 667,363 -> 73,991",
                                "avoid": ["romio_cb_read=enable (-70% read BW)", "romio_ds_write=disable (352 -> 95 MiB/s, FATAL)"]},
        "lustre_hdf5_shared_baseline": {"filesystem": "Lustre", "scale": "8 nodes x 64 ranks",
                                        "ior_flags": "-a HDF5 -b 64m -t 16m -s 8 -c", "result": "32 GiB shared file: write 2197 MiB/s / 14.9s, read 1332 MiB/s / 24.6s (2026-07-06)",
                                        "levers": "collective buffering usually helps on Lustre; lfs setstripe is the key L3 lever"},
        "lustre_hdf5_fpp_4k": {"filesystem": "Lustre", "scale": "512 ranks / 8 nodes", "ior_flags": "-a HDF5 -b 16m -t 4k -s 32 -C -F",
                               "result": "v0 write median 28905 MiB/s, read 17143 MiB/s (HDF5 1.14.5, n=7); no lever (align1m, coll-metadata, ROMIO cb, shm collectives, NIC/NUMA, ds, striping) beats baseline outside noise"},
    },
    "notes": [
        "stat -f -c %T the output dir first: VAST ROMIO rules do not apply on Lustre",
        "IOR deletes its test files unless -k: pass -k to verify written volume with du",
        "tracing state (DFTRACER_ENABLE / mode) must be identical across every A/B arm",
        "session_build_annotated runs its own configure without IOR's flags: build the annotated tree by hand",
        "dftracer setup.py ignores CMAKE_ARGS and pip --config-settings=cmake.args (silent all-OFF build): use DFTRACER_* env vars",
    ],
}

# rule kinds: forbid (regex must not match any command), require (regex must match some command; only when `when` matches, if given)
RULES = [
    {"id": "autoreconf_include_config", "forbid": r"\bautoreconf\b(?!.*-I\s*config)",
     "why": "X_AC_META lives in config/: 'X_AC_META: command not found', 'cannot find install-sh'",
     "fix": "touch NEWS AUTHORS && autoreconf -fi -I config"},
    {"id": "fcommon", "require": r"-fcommon", "when": r"(?:^|\s|/)configure\b(?!\.ac)",
     "why": "aiori.h defines globals without extern: 'ld.lld: error: duplicate symbol: posix_aiori'",
     "fix": "CFLAGS=\"... -fcommon\" (and make clean before rebuilding with new CFLAGS)"},
    {"id": "bfd_linker", "require": r"-fuse-ld=bfd", "when": r"(?:^|\s|/)configure\b(?!\.ac)",
     "why": "clang/lld rejects IOR's duplicate symbols", "fix": "LDFLAGS=\"-fuse-ld=bfd ...\""},
    {"id": "with_hdf5_yes_no", "forbid": r"--with-hdf5=(?!yes\b|no\b)\S+",
     "why": "--with-hdf5 takes yes/no; a path leaves USE_HDF5_AIORI false and silently drops the HDF5 backend",
     "fix": "--with-hdf5=yes plus CPPFLAGS=-I<hdf5>/include LDFLAGS=\"-L<hdf5>/lib -Wl,-rpath,<hdf5>/lib\""},
    {"id": "init_null_args", "forbid": r"DFTRACER_C_INIT\([^)]*-1|init_args\s*=\s*\"?[^\"]*-1",
     "why": "process_id is int *: DFTRACER_C_INIT(NULL,NULL,-1) is an int-to-pointer error / segfault",
     "fix": "DFTRACER_C_INIT(NULL, NULL, NULL); clang_annotate_project init_args=\"NULL, NULL, NULL\""},
    {"id": "annotated_link_lib", "require": r"LIBS=[\"']?[^\"'\n]*-ldftracer_core", "when": r"-I\S*dftracer|dftracer_inc",
     "why": "no libdftracer.pc: without LIBS=-ldftracer_core the link fails on initialize_main, finalize, initialize_region ...",
     "fix": "LIBS=\"-ldftracer_core -lstdc++\""},
    {"id": "annotated_no_as_needed", "require": r"--no-as-needed", "when": r"LIBS=[\"']?[^\"'\n]*-ldftracer_core",
     "why": "C main uses no C++: --as-needed drops -lstdc++ -> 'undefined reference ...@GLIBCXX_3.4.26'",
     "fix": "LDFLAGS += -Wl,--allow-shlib-undefined -Wl,--no-as-needed; LIBS += -lstdc++"},
    {"id": "dftracer_env_not_cmake_args", "forbid": r"CMAKE_ARGS=.*DFTRACER|config-settings=cmake\.args",
     "why": "dftracer's setup.py ignores CMAKE_ARGS and --config-settings=cmake.args (silent all-OFF build)",
     "fix": "export DFTRACER_ENABLE_MPI=ON DFTRACER_ENABLE_HDF5=ON DFTRACER_ENABLE_FTRACING=ON before pip install"},
    {"id": "dftracer_hip_off", "require": r"DFTRACER_ENABLE_HIP_TRACING=OFF", "when": r"pip\s+install.*dftracer",
     "why": "session_install_dftracer / default build auto-enables HIP tracing: rocprofiler-sdk/buffer.h missing is fatal",
     "fix": "export DFTRACER_ENABLE_HIP_TRACING=OFF DFTRACER_DISABLE_HWLOC=ON"},
    {"id": "unload_cray_hdf5", "require": r"module\s+unload\s+cray-hdf5-parallel", "when": r"DFTRACER_ENABLE_HDF5=ON",
     "why": "the Cray cc wrapper re-injects the unpatched HDF5 include (chid_t typo) ahead of the patched copy",
     "fix": "module unload cray-hdf5-parallel before the dftracer build"},
    {"id": "vast_no_ds_write_disable", "forbid": r"(?i)romio_ds_write=disable.*vast|vast.*romio_ds_write=disable",
     "why": "on VAST NVMe disabling data sieving forces small writes: write 352 -> 95 MiB/s (2026-06-24)",
     "fix": "leave romio_ds_write unset; use only *:romio_cb_write=enable"},
    {"id": "vast_no_cb_read", "forbid": r"(?i)romio_cb_read=enable.*vast|vast.*romio_cb_read=enable",
     "why": "on VAST collective read buffering cut read BW -70% (2163 -> 659 MiB/s)", "fix": "drop romio_cb_read"},
    {"id": "analyze_single_worker", "forbid": r"cluster_n_workers\s*=\s*(?:[2-9]|\d{2,})",
     "why": "dfanalyzer workers race on .dftindex and silently ingest a partial subset (2.96M / 8.69M vs 40.7M ops)",
     "fix": "cluster_type=local cluster_n_workers=1 (or default sizing inside an allocation)"},
    {"id": "no_cluster_cores", "forbid": r"cluster_cores", "why": "cluster_cores is not a valid analyze key",
     "fix": "drop cluster_cores"},
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
    def workload_ior_recipe(variant: str = "") -> dict:
        """Predictor: the IOR 4.0.0 recipe dftracer-agents verified (autoreconf bootstrap, -fcommon/-fuse-ld=bfd configure,
        HDF5 backend, annotated-build link chain, dftracer MPI+HDF5 install on Tuolumne, annotation rules, smoke, trace and
        analyze settings) as structured JSON. variant: optional, one of vast_hdf5_romio_opt, lustre_hdf5_shared_baseline,
        lustre_hdf5_fpp_4k (measured configs). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_ior_check(commands: list) -> dict:
        """Validator: check a proposed IOR recipe or command list against the skill's rules (autoreconf -I config, -fcommon,
        -fuse-ld=bfd, --with-hdf5=yes not a path, INIT(NULL,NULL,NULL), LIBS=-ldftracer_core + --no-as-needed, dftracer env
        vars not CMAKE_ARGS, HIP tracing off, cray-hdf5 unloaded, VAST ROMIO no-gos, single-worker analyze). commands: list of
        shell lines (or one newline-separated string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)
