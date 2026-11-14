"""Tuolumne (LLNL, AMD MI300A, Cray PE, flux, one Rabbit per 16-node chassis) and the systems of its family that share
the software stack (hetchy): the runtime library path a Cray-MPICH binary needs, Rabbit capacity sizing, and a check of
a planned Rabbit job against the rules learnt running on it."""
import glob
import json
import math
import os
import re

GIB = 1024 ** 3


def _vkey(p):
    return [int(x) for x in re.findall(r"\d+", p.split("/papi/")[1].split("/")[0])] or [0]


def runtime_dirs(extra=None):
    """Cray PE runtime dirs that exist here (the PAPI 'default' link, else the newest version), then `extra`."""
    dirs = [d for d in ("/opt/cray/pe/lib64", "/opt/cray/lib64") if os.path.isdir(d)]
    papi = "/opt/cray/pe/papi/default/lib64"
    if not os.path.isdir(papi):
        found = sorted(glob.glob("/opt/cray/pe/papi/*/lib64"), key=_vkey)
        papi = found[-1] if found else ""
    if papi:
        dirs.append(papi)
    return dirs + [e for e in (extra or []) if e]


def capacity(fs_type, nodes, ppn, bytes_per_rank, copies=1, margin=1.25):
    """#DW capacity: per compute node for xfs/gfs2/raw (ppn ranks write there), total for lustre; margin covers
    metadata and repeated iterations (an undersized request ends in ENOSPC or 'Access denied')."""
    per_node = ppn * bytes_per_rank * copies * margin
    need = per_node * (nodes if fs_type == "lustre" else 1)
    gib = max(1, math.ceil(need / GIB))
    return {"status": "ok", "fs_type": fs_type, "capacity": f"{gib}GiB", "scope": "total for the job" if fs_type == "lustre"
            else "per compute node", "bytes_needed": int(need)}


def check_job(nodes, queue, purpose, fs, flags):
    faults, notes = [], []
    fs = [dict(f) for f in fs]
    if purpose == "evidence" and queue != "pbatch":
        faults.append({"what": f"evidence runs for the corpus go on pbatch, not {queue}", "fix": "queue=pbatch"})
    if purpose in ("reproducer", "validation", "smoke") and queue not in ("pdebug", ""):
        notes.append(f"{purpose} runs usually go on pdebug (short); {queue} is fine only if pdebug cannot hold it")
    chassis = -(-nodes // 16)
    for f in fs:
        if f.get("type") == "gfs2" and f.get("profile") == "shared":
            if nodes > 16:
                faults.append({"what": f"shared gfs2 on {nodes} nodes: gfs2 is shared only within one chassis (16 nodes)",
                               "fix": "<= 16 nodes on --coral2-chassis=1, or Rabbit lustre for more"})
        if f.get("type") == "lustre" and f.get("profile") not in (None, "", "default", "shared"):
            faults.append({"what": f"lustre profile={f['profile']}: production systems have only the default profile",
                           "fix": "omit profile= (or profile=default)"})
        if f.get("name") and re.search(r"[A-Z]", f["name"]):
            notes.append(f"the mount env var is DW_JOB_{f['name'].replace('-', '_')} - case-sensitive, use it exactly")
    fl = " ".join(flags)
    if fs and "--coral2-chassis" not in fl:
        faults.append({"what": "a Rabbit job without --coral2-chassis", "fix": f"--coral2-chassis={chassis} (ceil(nodes/16))"})
    for m in re.finditer(r"(?:^|\s)-x\s+([A-Za-z_][A-Za-z0-9_]*)", fl):
        faults.append({"what": f"`-x {m.group(1)}`: -x is --exclusive in flux, so {m.group(1)} becomes the command to run",
                       "fix": f"--env={m.group(1)}"})
    if "--requires=-badrabbit" in fl:
        notes.append("--requires=-badrabbit is redundant: the site plugin already adds 'not badrabbit' to every job")
    if fs and "--exclusive" not in fl and not re.search(r"(?:^|\s)-x(?:\s|$)", fl):
        notes.append("Rabbit jobs are submitted --exclusive")
    return {"status": "fail" if faults else "pass", "chassis": chassis, "faults": faults, "notes": notes}


def register(mcp):
    @mcp.tool()
    def tuolumne_runtime_env(extra_dirs_json: str = "") -> str:
        """LD_LIBRARY_PATH for a Cray-MPICH binary run outside a module-loaded shell (detached submitters, flux batch jobs
        from a bare environment): the Cray PE runtime dirs that exist on this node (PAPI default, else newest), then
        extra dirs (HDF5 lib, dftracer lib64, the app's libs).

        Use for every traced or Rabbit run of a compiled app (else "libmpi_cray.so.12: cannot open shared object file",
        and flux may still report the job COMPLETED). extra_dirs_json: JSON list. Returns JSON {status, dirs,
        LD_LIBRARY_PATH}.
        """
        d = runtime_dirs(json.loads(extra_dirs_json) if extra_dirs_json else None)
        return json.dumps({"status": "ok", "dirs": d, "LD_LIBRARY_PATH": ":".join(d)})

    @mcp.tool()
    def tuolumne_dw_capacity(fs_type: str, nodes: int, ppn: int, bytes_per_rank: int, copies: int = 1,
                             margin: float = 1.25) -> str:
        """The #DW jobdw capacity for a run: xfs/gfs2/raw per compute node (ppn x bytes_per_rank x copies x margin), lustre
        total for the job (x nodes), rounded up to GiB.

        Use whenever a Rabbit filesystem is requested for an app or benchmark. bytes_per_rank: bytes one rank writes
        there; copies: iterations or checkpoints kept. Returns JSON {status, fs_type, capacity, scope, bytes_needed}.
        """
        if fs_type not in ("xfs", "gfs2", "raw", "lustre"):
            return json.dumps({"status": "error", "error": "fs_type must be xfs, gfs2, raw or lustre"})
        return json.dumps(capacity(fs_type, int(nodes), int(ppn), int(bytes_per_rank), int(copies), float(margin)))

    @mcp.tool()
    def tuolumne_check_job(nodes: int, queue: str, purpose: str = "run", filesystems_json: str = "", flags_json: str = "") -> str:
        """Check a planned job on Tuolumne (or a system of its family) against the rules learnt there: queue by purpose
        (evidence -> pbatch, reproducers/validation -> pdebug), shared gfs2 only within one 16-node chassis, Rabbit jobs
        with --coral2-chassis=ceil(nodes/16), only the default Lustre profile, `-x VAR` misuse, redundant
        --requires=-badrabbit, case-sensitive DW_JOB_ names.

        Use before submitting. purpose: run|evidence|reproducer|validation|smoke; filesystems_json: JSON list of {type,
        profile, name}; flags_json: JSON list of the flux options. Returns JSON {status: pass|fail, chassis,
        faults:[{what, fix}], notes}.
        """
        return json.dumps(check_job(int(nodes), queue, purpose, json.loads(filesystems_json) if filesystems_json else [],
                                    json.loads(flags_json) if flags_json else []))


    @mcp.tool()
    def system_tuolumne_recipe(section: str = "") -> str:
        """The build/run/env recipe system_tuolumne knows, as structured JSON: compilers, dftracer, env_vars, filesystems, hardware, known_bad_versions, launcher, ld_library_path, modules, mpi, optimization, python_dl, rocm.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (compilers, dftracer, env_vars, filesystems, hardware, known_bad_versions, launcher, ld_library_path, modules, mpi, optimization, python_dl, rocm); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_tuolumne_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_TUOLUMNE_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_tuolumne", "sections": sorted(_SYSTEM_TUOLUMNE_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_TUOLUMNE_RULES]})

    @mcp.tool()
    def system_tuolumne_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_tuolumne's rules: flux_not_srun_mpirun; no_papi_7_3; papi_own_module_line; papi_dir_from_cray_prefix; no_c_include_path_env; ld_library_path_append; nccl_socket_ifname_hsi0; no_mpiio_hints_via_env_flag; no_recursive_find_system_trees; no_mpi4py_no_binary.

        Use on a proposed recipe or command list before running it, and after system_tuolumne_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_TUOLUMNE_judge(commands, _SYSTEM_TUOLUMNE_RULES))


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _SYSTEM_TUOLUMNE_judge(commands, rules):
    """Apply the rules (forbid / require / require_if / forbid_if regexes) to the proposed commands."""
    items = commands
    if isinstance(commands, str):
        s = commands.strip()
        if s[:1] in "[{":
            try:
                items = json.loads(s)
            except ValueError:
                items = s
    lines = [ln for ln in _flatten(items) if ln.strip()]
    if not lines:
        return {"status": "inconclusive", "checks": [], "verdicts": {},
                "detail": "no commands given: pass the proposed command lines or recipe"}
    text = "\n".join(lines)
    out, verdicts = [], {}
    for r in rules:
        fl = re.I if "i" in r.get("flags", "") else 0
        pat = re.compile(r["pattern"], fl)
        when = re.compile(r["when"], fl) if r.get("when") else None
        kind = r["kind"]
        applies = when is None or bool(when.search(text))
        ok, detail = True, "not applicable"
        if applies and kind in ("forbid", "forbid_if"):
            bad = [ln for ln in lines if pat.search(ln)]
            ok = not bad
            detail = ("found: " + bad[0][:160]) if bad else "absent, as required"
        elif applies and kind in ("require", "require_if"):
            ok = bool(pat.search(text))
            detail = "present" if ok else "missing: " + r["pattern"]
        verdicts[r["id"]] = "n/a" if not applies else ("pass" if ok else "fail")
        out.append({"check": r["id"], "ok": ok, "detail": detail if ok else detail + " -- " + r["why"],
                    "fix": "" if ok else r["fix"]})
    return {"status": "fail" if any(not c["ok"] for c in out) else "pass", "checks": out, "verdicts": verdicts}


_SYSTEM_TUOLUMNE_RECIPE = {'hardware': {'node': 'AMD MI300A APU: 96 physical cores (no hyperthreading), 4 GPUs, ~502 GB unified CPU+GPU HBM',
              'apu': 'CPU and GPU share the same HBM: no host-device copy; pinned-memory / cross-NUMA levers are '
                     'structurally inert',
              'nics': {'hsi0': 'Slingshot-11 fabric, 200000 Mb/s',
                       'enp129s0': 'management, 1000 Mb/s (RCCL picks it by default)'},
              'ib_verbs': 'none (ibv_devices returns zero devices)',
              'no_sudo': True,
              'gpu_perf_level': 'not tunable by users: power_dpm_force_performance_level reads auto and is not '
                                'writable; rocm-smi --setperflevel is admin-only and rocm-smi is not on PATH even '
                                'after module load rocm',
              'rabbit': 'near-node NVMe per 16-node chassis (xfs/gfs2/lustre via #DW): see tuolumne_dw_capacity, '
                        'tuolumne_check_job and system_tuolumne_rabbit'},
 'modules': {'base_stack_order': ['craype-x86-trento',
                                  'libfabric/match_SHS',
                                  'craype-network-ofi',
                                  'perftools-base/25.09.0',
                                  'craype/2.7.35',
                                  'PrgEnv-cray/8.7.0',
                                  'flux_wrappers/0.1',
                                  'xpmem/2.6.5',
                                  'cce/20.0.0',
                                  'cray-libsci/25.09.0',
                                  'cray-mpich/9.0.1',
                                  'python/3.13.2'],
             'base_stack_note': 'order matters for Cray PE; StdEnv is loaded by default - do not reload it (check: '
                                'module list | grep StdEnv)',
             'dl_stack': 'ml cce/21.0.0 cray-mpich/9.1.0 rocm/7.1.1 rccl/fast-env-slows-mpi (PyTorch apps: reuse the '
                         "app's own install script stack verbatim)",
             'dl_stack_inactive': 'loading the dl_stack deactivates cray-hdf5-parallel/1.14.3.7 (and cray-hdf5): '
                                  'build HDF5 from source',
             'most_constrained_first': 'load the most constrained module first (e.g. rccl/fast-env-slows-mpi) and '
                                       'let lmod pick cce/cray-mpich/rocm',
             'papi': {'pin': 'papi/7.2.0.2 (module default: 30 presets incl. cache/TLB/branch/FP)',
                      'never': 'papi/7.3.0.1 (SIGSEGV in PAPI_library_init)',
                      'load': 'LAST, on its own `module load papi/7.2.0.2` line (in the same command as '
                              'cce/cray-mpich/rocmcc it is silently dropped)',
                      'env': 'export PAPI_DIR=${CRAY_PAPI_PREFIX} (the modulefile exports only CRAY_PAPI_PREFIX; '
                             'distro papi 5.6 in /usr/include, /lib64 otherwise wins)'},
             'inactive_guard': "INACTIVE=$(module list 2>&1 | awk '/Inactive Modules/{f=1; next} f && /^$/{f=0} "
                               'f{print}\'); [ -n "$INACTIVE" ] && { echo "ERROR: Inactive modules: $INACTIVE" >&2; '
                               'exit 1; }',
             'discovery': ['module avail <name>',
                           'module spider <name>',
                           'module show <module/ver>',
                           'never find /usr/tce, /opt/cray, /opt/rh (huge trees: exhaust resources / time out)'],
             'inactive_policy': {'hdf5_or_data_library': 'source install into the session prefix',
                                 'mpi_or_compiler': 'never source install: find a compatible module combination '
                                                    '(module spider prerequisite chain)'}},
 'compilers': {'default': 'CCE 20.0.0 (Cray clang 20.1.6) under PrgEnv-cray/8.7.0; DL apps use cce/21.0.0',
               'cc_cxx': 'after the module load, in the SAME script: export CC=$(which mpicc); export CXX=$(which '
                         'mpic++) (Cray wrappers); bind them to the MPI the app uses - a dftracer linked against '
                         'another MPI aborts at exit (double free)',
               'gnu_fallback': {'when': 'Cray clang 20 consteval error in spdlog/fmt (C++20), or Fortran apps '
                                        'failing with ftn/craycc',
                                'modules': 'module swap PrgEnv-cray PrgEnv-gnu; module load gcc-native/11.2',
                                'CC': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicc',
                                'CXX': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpicxx',
                                'FC': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/bin/mpif90 (+ FFLAGS '
                                      '-fallow-argument-mismatch)',
                                'only_gnu_dir': 'gnu/11.2 is the only cray-mpich 9.0.1 GNU wrapper dir; gcc-native '
                                                '12/12.1/12.2/13/13.2 exist but have none',
                                'cmake': 'rm -rf the CMake build dir before switching compiler (CMakeCache.txt pins '
                                         'it)'},
               'cray_clang_libstdcxx': 'Cray clang borrows C++ headers from /opt/rh/gcc-toolset-13 (mpicxx -v: '
                                       'Selected GCC installation)',
               'include_paths': 'never C_INCLUDE_PATH / CPLUS_INCLUDE_PATH (breaks the #include_next <stdlib.h> '
                                'chain); use -I<dir> in CFLAGS/CXXFLAGS',
               'mpicc_after_restack': 'after the module stack changes (e.g. to cce/21 + cray-mpich/9.1.0) re-run '
                                      'session_detect with mpicc/mpicxx pinned, e.g. '
                                      '/opt/cray/pe/mpich/9.1.0/ofi/crayclang/20.0/bin/mpicc'},
 'rocm': {'installed': 'every release /opt/rocm-4.2.0 ... /opt/rocm-7.2.1 side by side; the oldest has no CMake '
                       'config files',
          'pick': 'newest from `module avail -t rocm` (currently up to rocm/7.2.1); load the module (puts hipcc and '
                  'CMake config on PATH)',
          'seen_in_sessions': {'rocm/7.1.1': 'PyTorch app stacks (ROCM_PATH=/opt/rocm-7.1.1)',
                               'rocm-6.4.2': 'PAPI/rocprofiler-sdk 0.6.0 tests 2026-08-12',
                               'rocm-6.3.1': 'HIP tracing headers present 2026-07-20',
                               'rocm/7.2.1': 'RAJAPerf HIP 2026-08-04'},
          'hip_tracing_flag': 'DFTRACER_ENABLE_HIP_TRACING=ON only if the APP SOURCE uses HIP (hip_runtime.h, '
                              'hipMalloc, find_package(HIP), .hip files), not because ROCm exists on the node',
          'env_sh': 'the session env.sh must load the resolved rocm/X.Y.Z when HIP is needed; an env.sh created '
                    'before HIP detection is stale - remove scripts/env.sh and regenerate',
          'torch_bundled': 'PyTorch ROCm wheels load their own torch/lib/*.so (rocblas, MIOpen, rccl, ...), not '
                           '/opt/rocm',
          'sys_perfmon_warning': "'could not be locked for profiling due to lack of permissions (capability "
                                 "SYS_PERFMON)' degrades PMC counters only; rocprofv3 --kernel-trace works"},
 'mpi': {'library': 'cray-mpich/9.0.1 over OFI (craype-network-ofi, libfabric/match_SHS); DL stacks cray-mpich/9.1.0',
         'lib_dirs': {'MPI_LIB': '/opt/cray/pe/mpich/9.0.1/ofi/cray/20.0/lib',
                      'CCE_LIB': '/opt/cray/pe/cce/20.0.0/cce/x86_64/lib',
                      'gnu_mpi_lib': '/opt/cray/pe/mpich/9.0.1/ofi/gnu/11.2/lib',
                      'pe_lib64': '/opt/cray/pe/lib64'},
         'discover_hints': 'strings /opt/cray/pe/mpich/9.0.1/ofi/cray/20.0/lib/libmpi_cray.so | grep -E '
                           "'^romio_|^cb_|^striping_|^ind_|^ds_' | sort -u",
         'hints_available': ['romio_cb_write',
                             'romio_cb_read',
                             'romio_ds_write',
                             'romio_ds_read',
                             'cb_buffer_size',
                             'cb_nodes',
                             'cb_config_list',
                             'striping_factor',
                             'striping_unit',
                             'ind_rd_buffer_size',
                             'ind_wr_buffer_size',
                             'romio_lustre_cb_lock_ahead_write',
                             'romio_lustre_cb_lock_ahead_read',
                             'romio_lustre_cb_lock_ahead_num_extents',
                             'romio_no_indep_rw'],
         'hints_format': "MPICH_MPIIO_HINTS='<pattern>:key=value:key=value,<pattern2>:key=value' e.g. "
                         "'*:romio_cb_write=enable:cb_buffer_size=67108864:cb_nodes=16:romio_ds_write=disable:striping_factor=16:striping_unit=4194304'",
         'hints_delivery': 'export inside a wrapper script; never --env MPICH_MPIIO_HINTS=... on flux run (colons '
                           'are misinterpreted)',
         'hints_display': 'MPICH_MPIIO_HINTS_DISPLAY=1 prints the REQUESTED values, not what the runtime used',
         'cb_nodes': 'Cray MPICH ignores cb_nodes alone: pair with CRAY_CB_NODES_MULTIPLIER; keep striping_unit '
                     'equal to the real stripe size',
         'mpi4py_py313': 'mpi4py==4.1.1 manylinux wheel extracted by hand + patchelf --replace-needed libmpi.so.12 '
                         'libmpi_cray.so on MPI.mpich.*.so + export MPI4PY_MPIABI=mpich; never --no-binary=mpi4py'},
 'ld_library_path': {'store_tool': 'tuolumne_runtime_env(extra_dirs_json) -> /opt/cray/pe/lib64, /opt/cray/lib64, '
                                   'PAPI default lib64, then extras (preferred, newer)',
                     'cce_fix': 'export '
                                'LD_LIBRARY_PATH=/opt/cray/pe/cce/20.0.0/cce/x86_64/lib:/opt/cray/pe/cce/20.0.0/cce/x86_64/lib/default64:/usr/lib64:${LD_LIBRARY_PATH}',
                     'flux_run_env': 'flux run --env '
                                     'LD_LIBRARY_PATH=${CCE_LIB}:${CCE_LIB}/default64:${MPI_LIB}:/opt/cray/pe/lib64:${EXTRA_LIBS} '
                                     '<cmd>',
                     'append_never_replace': 'after `source <ws>/scripts/env.sh`: export LD_LIBRARY_PATH="<session '
                                             'libs>:${LD_LIBRARY_PATH}" (a replace drops cray-mpich/cray-pmi dirs)',
                     'session_order': 'session-local libs (HDF5 lib, dftracer lib64) FIRST so they shadow '
                                      'system/anaconda copies',
                     'every_step': 're-export at every step/subprocess including the session dftracer lib64 (find '
                                   "<venv> -name 'libdftracer_core.so*'); prefer -Wl,-rpath when it keeps recurring",
                     'usr_lib64': "/usr/lib64 on LD_LIBRARY_PATH also works around anaconda compiler_compat/ld's "
                                  'broken sysroot (undefined ZSTD_*)'},
 'filesystems': {'lustre': {'path': '/p/lustre5/$USER',
                            'use': 'ALL benchmark/app data, datasets, checkpoints, core files, run output',
                            'ior': 'mkdir -p /p/lustre5/$USER/workspaces/ior; '
                                   'DATA_DIR=/p/lustre5/$USER/workspaces/ior',
                            'dl': 'mkdir -p /p/lustre5/$USER/workspaces/<app>/{fractals,datasets,runs,traces}',
                            'readahead': 'llite max_read_ahead_mb already 512 per client; per-file readahead '
                                         'admin-only',
                            'dom': 'default Data-on-MDT PFL already covers small metadata-heavy files'},
                 'nfs_workspace': {'path': '${WORKSPACE}/workspaces/<session>/ (project dir on NFS)',
                                   'use': 'sources, builds, tmp (workspaces/<session>/tmp/), session traces/ dir',
                                   'note': 'small and fills up; a venv there is NFS (stat -f -> Type: nfs) and '
                                           'import storms cost metadata time; never write /tmp directly'},
                 'vast_archive': {'path': '/p/vast1/$USER/dftracer-agents/<rel>',
                                  'use': 'archive finished bulky traces, symlink back to the workspace path',
                                  'verify': 'regular-file bytes + rsync dry-run, never du (NFS vs VAST '
                                            'directory-inode sizes differ)'},
                 'striping': {'cmd': 'lfs setstripe -c 16 -S 4M /p/lustre5/$USER/<app>/<run>',
                              'verify': 'lfs getstripe -d <dir>',
                              'rule': 'stripe the OUTPUT DIRECTORY before the first file is created; fresh dir per '
                                      'iteration; inert for metadata-bound (open/stat) shapes'},
                 'large_ops': 'multi-GB/TB or >10k files on /p/lustre5: mpifileutils '
                              'dcp/dsync/drm/dwalk/dcmp/dtar/dstripe, not cp/rsync/rm -rf/diff -r/tar',
                 'core_dumps': 'ulimit -c unlimited; cd to a Lustre run dir; gdb|rocgdb <binary> core.<pid> (compute '
                               'nodes default to ulimit -c 0)'},
 'launcher': {'scheduler': 'flux only (flux_wrappers/0.1 loaded); no srun / mpirun / mpiexec',
              'quickref': ['flux queue list',
                           'flux resource info',
                           'flux alloc -N <N> -q <QUEUE> -t <TIME>',
                           'flux alloc --bg -N <N> -q <QUEUE> -t <TIME>',
                           'flux proxy <JOBID>',
                           'flux run -N <N> -n <TASKS> <CMD>'],
              'existing_allocation': 'flux proxy <alloc_id> flux run ... ; a bare flux run from a login shell '
                                     'submits a NEW job that queues (S)',
              'wrapper_script': 'write the payload to <ws>/tmp/<name>.sh (source /usr/share/lmod/lmod/init/bash '
                                'first, modules, exports, venv) then flux proxy <JOBID> bash <ws>/tmp/<name>.sh; '
                                'never bash -c with inline module loads',
              'scaling': 'use all nodes of the allocation and 96 ranks per node by default: N_NODES=$(flux proxy '
                         "<JOBID> flux resource list --format='{nnodes}' -s free | tail -1); -n $((N_NODES*96))",
              'gpu_jobs': 'flux alloc -g 1 per task for GPU-bound jobs; torchrun-hpc -N <n> -n 4 --gpus-per-proc 1 '
                          '...',
              'dftracer_service_cores': 'reserve one core per node for dftracer_service: -c 23 for 4 ranks/node (24 '
                                        'hangs the job in S forever)',
              'pin_hosts': 'inside a larger allocation pin service start / app / stop to the same hosts: '
                           '--requires=host:<h1>,<h2>,... --setattr=exclusive=false',
              'busy_nodes': "flux proxy <alloc> flux jobs --filter=running -no '{nodelist}' (flux resource list "
                            'shows the cluster, not the allocation)',
              'long_utils': 'large dftracer-utils split/index runs on the login node or an allocation with ample '
                            'time left',
              'store_rules': 'queue / chassis / Rabbit / -x VAR rules: tuolumne_check_job'},
 'python_dl': {'env_steps': ["1 load the app's module stack (source its install script / module block)",
                             '2 session-local libs first on LD_LIBRARY_PATH (e.g. ${SESSION}/install/hdf5/lib)',
                             '3 source ${SESSION}/install/bin/activate (ONE venv for app + dftracer + deps)',
                             'install only: 4 CC/CXX = mpicc/mpic++, 5 one pip install of everything, 6 ldd every '
                             'C-extension .so'],
               'install_extras': 'pip install .[rocmwci] (prebuilt WCI wheel)',
               'patchelf': {'libmagma/libomp': 'patchelf --add-rpath /opt/rocm-7.1.1/llvm/lib <so>',
                            'mpi4py segfault': 'patchelf --replace-needed libmpi_gnu_112.so.12 libmpi_gnu.so.12 '
                                               '<torch_lib>/*.so*',
                            'cblas_gemm_f16f16f32': 'patchelf --add-rpath /opt/intel/oneapi/mkl/2024.2/lib '
                                                    '<torch_lib>/*.so*',
                            'no_ld_preload': 'fix library issues with patchelf, not LD_PRELOAD'},
               'h5py': 'HDF5_DIR=${SESSION}/install/hdf5 pip install --no-binary=h5py h5py, then patchelf '
                       "--set-rpath ${SESSION}/install/hdf5/lib on every h5py .so (pip put anaconda's lib first); "
                       'verify objdump -p <so> | grep RUNPATH',
               'hdf5_source': 'hdf5-1.14.5: ./configure --prefix=<WS>/install/hdf5 --enable-shared --disable-static; '
                              'make -j8 install',
               'dftracer_hdf5': 'patchelf dftracer libdftracer_core.so / libdftracer_preload.so --replace-needed '
                                'libhdf5.so.103 libhdf5.so.310 + --set-rpath session HDF5; never '
                                'DFTRACER_DISABLE_IO=1',
               'miopen_warmup': {'MIOPEN_DEBUG_CONV_DIRECT_NAIVE_CONV_FWD': '0',
                                 'MIOPEN_DEBUG_CONV_DIRECT_NAIVE_CONV_BWD': '0',
                                 'MIOPEN_DEBUG_CONV_DIRECT_NAIVE_CONV_WRW': '0'},
               'rccl': 'export NCCL_SOCKET_IFNAME=hsi0 for multi-node NCCL/RCCL; verify with NCCL_DEBUG=INFO '
                       'NCCL_DEBUG_SUBSYS=INIT,NET; NCCL_NET_GDR_LEVEL/CXI tuning inert without aws-ofi-rccl',
               'dataloader_fork': 'plain pip h5py bundles fork-unsafe HDF5; temporary workaround '
                                  "multiprocessing_context='spawn', permanent fix source HDF5",
               'torch_profiler': 'GPU-kernel visibility under DDP: torch.profiler with '
                                 'on_trace_ready=dftracer.python.torch.trace_handler (cat PP)'},
 'dftracer': {'install_2026_11': ['source ${WORKSPACE}/scripts/env.sh',
                                  'pip install --pre "dftracer[modules]" dftracer-modules',
                                  'dftracer-compose --enable mpi,hdf5,hip --disable papi,hwloc,cuda',
                                  'dftracer_install_info --composition'],
              'same_venv': "Python/ML apps: dftracer in the app's venv (ws/install), never a separate venv",
              'init_mode': 'DFTRACER_INIT=FUNCTION; HYBRID with LD_PRELOAD=<venv>/.../libdftracer_preload.so only as '
                           'fallback on an empty trace; never PRELOAD-only (Python apps)',
              'verify': "python -c 'import dftracer.dftracer' and a NON-EMPTY .pfw; zero exit code is not proof",
              'hip_tracing': 'fixed 2026-08-13: libdftracer_core exports rocprofiler_configure (nm -D --defined-only '
                             'libdftracer_core.so | grep rocprofiler_configure); all 5 kinds fire',
              'papi': {'pin_module': 'papi/7.2.0.2',
                       'PAPI_DIR': '${CRAY_PAPI_PREFIX}',
                       'teardown_segv': 'branches without the finalize-order fix (feature/papi-counter-tracing as of '
                                        '2026-08-13) lose 1-3 of 16 ranks at exit on multi-minute runs; '
                                        'DFTRACER_ENABLE_PAPI_TRACING=0 for full-rank traces; count zero-byte '
                                        '*-app.pfw.gz'},
              'service': {'stop_before_start': 'dftracer_service stop <state_dir> before start (daemons survive flux '
                                               'cancel)',
                          'pid_files': '<state_dir>/dftracer_server_<hostname>.pid (flat, not per-host subdirs)',
                          'verify': 'one non-empty service_<host>.pfw.gz per job node (flushed only on stop)'},
              'variorum': 'variorum (librocm_smi64.so.7) only in dftracer_service, never in libdftracer_core (hwloc '
                          'pulls librocm_smi64.so.1): ldd libdftracer_core.so | grep -c rocm_smi must be <= 1',
              'pip_index': 'PIP_CONFIG_FILE=/dev/null PIP_INDEX_URL=https://pypi.org/simple when a user pip config '
                           'adds an unreachable extra index',
              'traces': 'session traces/ dir in the workspace (pipeline rule); archive finished bulky trace dirs to '
                        'VAST'},
 'env_vars': {'NCCL_SOCKET_IFNAME': 'hsi0',
              'MPI4PY_MPIABI': 'mpich',
              'PAPI_DIR': '${CRAY_PAPI_PREFIX}',
              'MPICH_MPIIO_HINTS': 'see mpi.hints_format',
              'MPICH_MPIIO_HINTS_DISPLAY': '1 (requested values only)',
              'CRAY_CB_NODES_MULTIPLIER': 'raise MPI-IO aggregators with cb_nodes',
              'ROCM_PATH': '/opt/rocm-<ver> matching the loaded rocm module',
              'DFTRACER_INIT': 'FUNCTION (HYBRID fallback)',
              'DFTRACER_ENABLE_PAPI_TRACING': '0 to avoid the teardown race on unfixed branches',
              'forbidden': ['C_INCLUDE_PATH',
                            'CPLUS_INCLUDE_PATH',
                            'DFTRACER_DISABLE_IO=1',
                            'HSA_ENABLE_INTERRUPT=0 (mixed CPU+GPU apps)',
                            "PIP_EXTRA_INDEX_URL='' (does not override a config file)"]},
 'optimization': {'axes_order': ['overlap compute and I/O (prefetch, persistent_workers, async checkpoint)',
                                 'file layout / access pattern (fewer opens/stats, shard small files)',
                                 'system utilization (striping, DoM, memory bandwidth roofline)',
                                 'compute (AMP, MIOpen tuning, then algorithms)'],
                  'inert_levers': ['launcher-level CPU affinity (flux cpu-affinity, torchrun-hpc binding) - measured '
                                   'null 3x',
                                   'pinned host memory / cross-NUMA placement on the APU',
                                   'Lustre client readahead (already max)',
                                   'GPU perf level / clocks (not writable)',
                                   'HSA_ENABLE_INTERRUPT=0 (net regression unless pure-GPU)',
                                   'OST striping / cb_nodes for metadata-bound shapes',
                                   'prewarming /opt/rocm libs for PyTorch (it loads torch/lib)'],
                  'affinity_if_tested': "cores_per_rank = 96 / 4; bind rank i to GPU i's die and treat pin_memory + "
                                        'affinity as ONE change',
                  'measurement': 'one change per run; run the control CONCURRENTLY on a same-size allocation '
                                 '(identical control varied 141 s vs 293 s 30 min apart); >= 5 interleaved '
                                 'replicates; check event/byte counts before crediting a wall-clock win'},
 'known_bad_versions': {'papi/7.3.0.1': 'SIGSEGV in PAPI_library_init (rocp_sdk ABI vs rocprofiler-sdk 0.6.0 of ROCm '
                                        '6.4.2)',
                        'cce/20.0.0 (clang 20.1.6)': "consteval error in spdlog's bundled fmt (C++20)",
                        'Cray ftn/craycc': 'Fortran apps (Flash-X) fail: use GNU MPI wrappers',
                        '/opt/rocm-4.2.0': 'oldest install, no CMake config: never auto-pick lexically',
                        'mpi4py<4.0': 'cannot build on Python 3.13',
                        'distro papi 5.6': '/usr/include/papi.h + /lib64/libpapi.so.5 picked when PAPI_DIR is unset'}}

_SYSTEM_TUOLUMNE_RULES = [{'id': 'flux_not_srun_mpirun',
  'kind': 'forbid',
  'pattern': '(^|[\\s;&|(])(srun|mpirun|mpiexec)\\s',
  'why': 'Tuolumne schedules and launches with flux only.',
  'fix': 'Launch with flux run -N <N> -n <tasks> (flux proxy <alloc> flux run ... inside an allocation).'},
 {'id': 'no_papi_7_3',
  'kind': 'forbid',
  'pattern': '\\bpapi/7\\.3',
  'why': 'papi/7.3.0.1 SIGSEGVs in PAPI_library_init (rocp_sdk built against another rocprofiler-sdk ABI) and kills '
         'the traced app.',
  'fix': 'module load papi/7.2.0.2 (the module default).'},
 {'id': 'papi_own_module_line',
  'kind': 'forbid',
  'pattern': '^\\s*(?:module\\s+load|ml)\\s+(?=[^#\\n]*\\bpapi\\b)\\S+\\s+\\S+',
  'why': 'papi loaded in the same command as cce/cray-mpich/rocmcc is silently dropped by the MODULEPATH reload '
         '(CRAY_PAPI_PREFIX empty).',
  'fix': 'Load papi LAST on its own line: module load papi/7.2.0.2.'},
 {'id': 'papi_dir_from_cray_prefix',
  'kind': 'require_if',
  'pattern': 'PAPI_DIR=["\']?\\$\\{?CRAY_PAPI_PREFIX',
  'when': '(module\\s+load|ml)\\s[^\\n]*\\bpapi\\b',
  'why': 'The papi modulefile exports only CRAY_PAPI_PREFIX; FindPAPI.cmake reads PAPI_DIR and otherwise finds the '
         'distro PAPI 5.6 header with a 7.x runtime.',
  'fix': 'export PAPI_DIR="${CRAY_PAPI_PREFIX}" after module load papi/7.2.0.2.'},
 {'id': 'no_c_include_path_env',
  'kind': 'forbid',
  'pattern': '\\b(C_INCLUDE_PATH|CPLUS_INCLUDE_PATH)=',
  'why': "C_INCLUDE_PATH/CPLUS_INCLUDE_PATH (even =/usr/include) break Cray clang's #include_next <stdlib.h> chain: "
         "'stdlib.h' file not found in every C++ TU.",
  'fix': 'Unset them and pass the extra include dir as -I<dir> in CFLAGS/CXXFLAGS.'},
 {'id': 'ld_library_path_append',
  'kind': 'forbid',
  'pattern': '^\\s*export\\s+LD_LIBRARY_PATH=(?![^\\n]*\\$\\{?LD_LIBRARY_PATH)',
  'why': 'Replacing LD_LIBRARY_PATH after module load drops the cray-mpich/cray-pmi dirs: libmpi_cray.so.12 / '
         'libpmi.so.0 cannot open shared object file.',
  'fix': 'Prepend and keep the tail: export LD_LIBRARY_PATH="<libs>:${LD_LIBRARY_PATH}" (or build it with '
         'tuolumne_runtime_env).'},
 {'id': 'nccl_socket_ifname_hsi0',
  'kind': 'require_if',
  'pattern': 'NCCL_SOCKET_IFNAME=["\']?hsi0',
  'when': 'torchrun|rccl|nccl|init_process_group',
  'flags': 'i',
  'why': 'No IB verbs and no aws-ofi-rccl plugin: RCCL uses sockets and picks the 1 GbE enp129s0 NIC before hsi0 '
         '(200 Gb/s) - inter-node collectives silently ~200x slower.',
  'fix': 'export NCCL_SOCKET_IFNAME=hsi0 in the run script (verify once with NCCL_DEBUG=INFO '
         'NCCL_DEBUG_SUBSYS=INIT,NET).'},
 {'id': 'no_mpiio_hints_via_env_flag',
  'kind': 'forbid',
  'pattern': '--env[= ]MPICH_MPIIO_HINTS=',
  'why': 'The colons in MPICH_MPIIO_HINTS are misinterpreted when passed through flux run --env.',
  'fix': 'export MPICH_MPIIO_HINTS inside a wrapper script and run flux proxy <JOBID> bash <ws>/tmp/<name>.sh.'},
 {'id': 'no_recursive_find_system_trees',
  'kind': 'forbid',
  'pattern': '\\bfind\\s+/(usr/tce|opt/cray|opt/rh)\\b',
  'why': 'Recursive searches of /usr/tce, /opt/cray, /opt/rh exhaust resources or time out.',
  'fix': 'Discover software with module avail / module spider / module show.'},
 {'id': 'no_mpi4py_no_binary',
  'kind': 'forbid',
  'pattern': '--no-binary[= ]?[^\\n]*mpi4py',
  'why': "On Python 3.13 + NFS a source mpi4py build succeeds but pip's rename of the .so fails ([Errno 2] No such "
         'file or directory).',
  'fix': 'pip download mpi4py==4.1.1 --no-deps, extract the wheel by hand, patchelf --replace-needed libmpi.so.12 '
         'libmpi_cray.so, export MPI4PY_MPIABI=mpich.'}]
