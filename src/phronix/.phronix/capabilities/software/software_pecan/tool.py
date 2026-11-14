"""software_pecan: PECAN (pose classification, PECAN/MILAN pose-classification / binding-affinity repo): PyTorch + PyTorch-Geometric EGNN DDP training on PDBspheres/PDBBind HDF5 shards, traced and optimized with dftracer on Tuolumne (MI300A, ROCm 6.3.1, Flux). Holds the venv/build recipe (python/3.11.5 for ROCm torch wheels, torch_scatter/torch_sparse with PYTORCH_ROCM_ARCH=gfx942 and plain GCC for torch_sparse), dataset permission workarounds, app bug fixes, the flux DDP launch and dftracer_service recipe, DataLoader worker tracing (spawn, worker_init_fn finalize), and every measured optimization result. Load for any PECAN / PDBspheres / PDBBind session, or on 'undefined symbol: _cray$mt_kmpc_fork_call_with_flags', 'Per-resource options can't be used with per-task options', a silent hung NCCL/RCCL rendezvous, 'flux run dftracer_service start' never returning, 'GLIBCXX_3.4.32 not found' with LD_PRELOAD, 0-byte DataLoader worker .pfw.gz files, 'Can't pickle local object ... _worker_init', a num_workers>2 deadlock, or 'ValueError: not enough values to unpack (expected 7, got 6)'."""
import json
import re


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _SOFTWARE_PECAN_judge(commands, rules):
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


def register(mcp):

    @mcp.tool()
    def software_pecan_recipe(section: str = "") -> str:
        """The build/run/env recipe software_pecan knows, as structured JSON: app_env_vars, app_fixes, classification, comparison_rules, dataloader_tracing, dataloader_tuning, dataset, dftracer_service, env_tuolumne, flux_launch, measured, optimization_backlog, pyg_extensions, scope, source.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (app_env_vars, app_fixes, classification, comparison_rules, dataloader_tracing, dataloader_tuning, dataset, dftracer_service, env_tuolumne, flux_launch, measured, optimization_backlog, pyg_extensions, scope, source); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_pecan_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_PECAN_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_pecan", "sections": sorted(_SOFTWARE_PECAN_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_PECAN_RULES]})

    @mcp.tool()
    def software_pecan_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_pecan's rules: python_311_for_rocm_torch; rocm_arch_for_pyg_ext; torch_sparse_plain_gcc; flux_no_mixed_per_resource_task; service_not_flux_run; service_no_tasks_per_node; master_addr_from_nodelist; python_unbuffered; service_env_exported; ld_preload_modern_libstdcxx.

        Use on a proposed recipe or command list before running it, and after software_pecan_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_PECAN_judge(commands, _SOFTWARE_PECAN_RULES))


_SOFTWARE_PECAN_RECIPE = {'source': {'repo': 'pecan_milan on LLNL czgitlab (PECAN + sibling MILAN)',
            'naming': 'software_ (not workload_) per software-vs-workload convention'},
 'scope': {'annotated_active': ['pecan/trainer.py', 'pecan/dataset.py (Dataset_PDB)'],
           'not_in_scope': ['milan/*.py',
                            '*_old.py',
                            'pecan/dataset_dyad*.py',
                            'pecan/datacopy_dyad*.py (DYAD in-transit staging)'],
           'model': 'model/egnn.py (nn_type=3) needs torch_geometric core only; model/model_trainer.py imports all '
                    'variants (sgcnn.py, ggcnn.py need torch_scatter/torch_sparse)'},
 'classification': {'session_build_tool': 'python-pip',
                    'why': 'pure Python tree, no setup.py/setup.cfg/pyproject.toml',
                    'flow': 'one shared venv, explicit dependency installs; no pip install -e <repo>',
                    'reclassify': {'pyproject mesonpy': 'meson / software_meson',
                                   'setuptools metadata': 'packaged python',
                                   'conda env files': 'anaconda inputs only, still one session venv'}},
 'env_tuolumne': {'system': 'Tuolumne MI300A',
                  'rocm': '6.3.1',
                  'python_module': 'python/3.11.5 (not default python/3.13.2)',
                  'torch_wheels': 'repo.radeon.com/rocm/manylinux/rocm-rel-6.3.1/ (cp39/cp310/cp311 only)',
                  'extra_pip': ['pyyaml']},
 'pyg_extensions': {'sources': {'torch_scatter': 'pytorch_scatter-2.1.2',
                                'torch_sparse': 'pytorch_sparse-0.6.18',
                                'location': 'pyg-rocm-build/ in the parent install repo; copy to a writable dir '
                                            'first'},
                    'env': {'PYTORCH_ROCM_ARCH': 'gfx942'},
                    'build_time': '~5-8 min each with gfx942, 30-60+ min without',
                    'torch_scatter': {'CC': 'mpicc', 'CXX': 'mpic++'},
                    'torch_sparse': {'modules': ['gcc-native/13'],
                                     'CC': 'gcc',
                                     'CXX': 'g++',
                                     'why': 'Cray OpenMP -> undefined symbol _cray$mt_kmpc_fork_call_with_flags'},
                    'install': "ignore trailing setup.py 'error: [Errno 2]'; pip install dist/*.whl"},
 'dataset': {'location': '$VAST_ROOT/data_pecan/ (PDBspheres/PDBBind HDF5 shards)',
             'index_csv': 'pdbspheres_all_0000000_all.csv may be rw------- while shards are rw-rw----',
             'fallback': 'train_fns: [list of .hdf5] instead of train_csvs',
             'benchmark_config': 'PDBspheres_v2_split8, 150 shards, batch_size=8, num_workers=2, 2 epochs, '
                                 'nn_type=3, train_csvs: null'},
 'app_env_vars': {'PECAN_INDEX_CSV_DIR': 'writable dir for the auto-derived index CSV (fix 2026-07-20)',
                  'PECAN_DECODE_CACHE': '1 (default) per-worker decoded-sample cache on; 0 off',
                  'PECAN_TORCH_COMPILE': 'default 1; set 0 in I/O runs while a compute job may edit the source tree',
                  'PECAN_PREFETCH_FACTOR': 'default 2 (torch default); 4 and 8 measured',
                  'PYTORCH_HIP_ALLOC_CONF': 'expandable_segments:True,garbage_collection_threshold:0.8 (harmless, no '
                                            'measured win)'},
 'app_fixes': ['Dataset_PDB h5-driven index CSV -> PECAN_INDEX_CSV_DIR / tempfile.gettempdir() on PermissionError '
               '(2026-07-20)',
               'use_crystal=True branch: append trailing 0.0 score (7 fields) (2026-07-20)',
               'per-worker h5py.File handle cache _get_h5 + __getstate__ dropping cache + persistent_workers=True '
               '(2026-07-20)',
               'attr-hoist of num_hbonds/hpbond/habond/sbond/pbond into data_list + decoded-sample cache keyed '
               '(pdbid, poseid), guarded off for modality==1 (2026-07-22)',
               'DataListLoader multiprocessing_context="spawn" (train+val, nn_type==3) (2026-07-22)',
               'top-level _dftracer_worker_init worker_init_fn on train+val loaders (2026-07-22)',
               'torch.stack([t.view(()) ...]) when replacing torch.FloatTensor(list) (2026-07-22)'],
 'flux_launch': {'ddp': 'flux run -N<nodes> -n<total_tasks> -g<gpus_per_task> python -u <script>',
                 'example': 'flux run -N4 -n16 -g1 python -u main_app.py <config>',
                 'never': '--tasks-per-node together with --gpus-per-task',
                 'master_addr': ['NODELIST=$(flux job info $FLUX_JOB_ID R | python3 -c "import json,sys; '
                                 'print(json.load(sys.stdin)[\'execution\'][\'nodelist\'][0])")',
                                 'export MASTER_ADDR=$(flux hostlist -n 0 "$NODELIST")'],
                 'master_addr_wrong': ['$(hostname)', 'flux getattr local-uri (local:// socket path)'],
                 'unbuffered': 'python -u (imports take 1-2 min across ranks)'},
 'dftracer_service': {'env': ['DFTRACER_ENABLE=1', 'DFTRACER_LOG_FILE=<dir>/<prefix>'],
                      'start': 'SVC_JOB=$(flux submit -N<n> -n<n> -c1 dftracer_service start <dir>)',
                      'wait': 'for _ in $(seq 1 30); do [ "$(ls <dir>/dftracer_server_*.pid 2>/dev/null | wc -l)" '
                              '-ge <n> ] && break; sleep 2; done',
                      'stop': 'flux submit -N<n> -n<n> -c1 dftracer_service stop <dir>  (in an EXIT trap)',
                      'never': ['flux run ... dftracer_service start (never returns)',
                                '--tasks-per-node (exclusive)'],
                      'verify': ['flux job info <id> jobspec has no "exclusive": true',
                                 'flux resource list',
                                 'non-empty per-node traces'],
                      'pid_files': 'dftracer_server_<hostname>.pid (dftracer develop 3e6fc42)',
                      'observed_version': 'dftracer 2.1.0.dev16'},
 'dataloader_tracing': {'worker_init_fn': 'top-level _dftracer_worker_init(worker_id): init_dftracer(); '
                                          'atexit.register(finalize_dftracer, logger); chain dataset.worker_init via '
                                          'torch.utils.data.get_worker_info().dataset',
                        'never': 'closure-returning factory (unpicklable under spawn)',
                        'side_effect': 'HIP Intercept context start failed: status, 2 once per worker (benign so '
                                       'far)',
                        'invalid': 'DFTRACER_INIT=HYBRID (not a ProfileInitType; only PROFILER_INIT_FUNCTION / '
                                   'PROFILER_INIT_LD_PRELOAD)',
                        'ld_preload': 'LD_PRELOAD=<anaconda3-2023.09>/lib/libstdc++.so.6:<dftracer_prefix>/lib/libdftracer_preload.so'},
 'dataloader_tuning': {'num_workers_fork_safe': 2,
                       'num_workers_spawn_validated': 6,
                       'prefetch_factor_validated': [4, 8],
                       'spawn_cost': 'epoch 1 82.05s -> 451.8s'},
 'measured': {'scale': '4 nodes x 4 GPU, 16-rank DDP (baseline5: 48 processes, job_time 144.03s)',
              'baseline_epoch2_s': 31.54,
              'results': [{'change': 'handle cache + persistent_workers',
                           'date': '2026-07-20',
                           'metric': 'work-normalized file-open rate -76.5%; H5Fopen 1.0 -> 0.03/sample'},
                          {'change': 'attr-hoist + decode cache',
                           'date': '2026-07-22',
                           'epoch2_s': 28.859,
                           'reps': 2,
                           'delta': '-8.5%',
                           'events': 'data-load-h5 -49.1%'},
                          {'change': 'attr-hoist only (PECAN_DECODE_CACHE=0)',
                           'date': '2026-07-22',
                           'epoch2_s': 32.577,
                           'reps': 3,
                           'delta': '+3.3% (no win)'},
                          {'change': 'PECAN_PREFETCH_FACTOR=4, num_workers=2',
                           'date': '2026-07-22',
                           'epoch2_s': 29.68,
                           'reps': 1},
                          {'change': 'spawn + num_workers=6 + PECAN_PREFETCH_FACTOR=8 (io_opt4)',
                           'date': '2026-07-22',
                           'epoch2_s': 20.27,
                           'reps': 1,
                           'delta': '-35.7%'},
                          {'change': 'worker_init_fn finalize (io_opt4_finalize)',
                           'date': '2026-07-22',
                           'epoch2_s': 29.72,
                           'traces': 'empty 32/80 -> 0/48'},
                          {'change': 'PYTORCH_HIP_ALLOC_CONF', 'date': '2026-07-22', 'delta': '+3.1% (noise)'}],
              'overlap': {'same_pid_sweep_line': '0% (methodology bug)',
                          'cross_process_buckets': '71.8% of compute overlapped, 28.2% (32.2s) residual stall',
                          'events': 32656,
                          'p99_dur_s': 0.412,
                          'buckets': 169},
              'not_bottlenecks': ['communication-except-io (25.58-30.68s, <1% of wall)',
                                  'cpu-gpu transfer / pin_memory (MI300A unified HBM)',
                                  'NUMA / launcher affinity',
                                  'memory bandwidth',
                                  'stdio_ops_slope (artifact)',
                                  'communication_io (nests HDF5 storm)']},
 'optimization_backlog': {'io': 'residual stall: num_workers / prefetch_factor; re-run overlap algorithm on post-fix '
                                'traces',
                          'compute_ranked': ['torch.compile(model, dynamic=True) (measure graph breaks, loss parity)',
                                             'trainer.py loss-block device-resident rewrite',
                                             'precompute graph adjacency to disk',
                                             'AMP bf16 (ceiling ~2%)'],
                          'not_applicable': ['torch.cdist swap (changes values)',
                                             'MIOpen autotune (no conv)',
                                             'EGNN gather/scatter cache-blocking (research-grade, deprioritized)'],
                          'replicates': '>=5 on an isolated allocation before crediting single-replicate wins'},
 'comparison_rules': ['same rank count as baseline',
                      'run completed (no job.exception cancel)',
                      'use epoch-2 steady state, not epoch 1',
                      'else work-normalized per-op ratios']}

_SOFTWARE_PECAN_RULES = [{'id': 'python_311_for_rocm_torch',
  'kind': 'forbid',
  'pattern': 'module\\s+load\\s+[^\\n]*python/3\\.(1[2-9]|[0-8])(\\.|\\s|$)',
  'why': 'ROCm 6.3.1 torch wheels exist only for cp39/cp310/cp311.',
  'fix': 'module load python/3.11.5.'},
 {'id': 'rocm_arch_for_pyg_ext',
  'kind': 'require_if',
  'pattern': 'PYTORCH_ROCM_ARCH=gfx942',
  'when': '(pytorch_scatter|pytorch_sparse|torch_scatter|torch_sparse)[^\\n]*(setup\\.py|bdist_wheel)|(setup\\.py|bdist_wheel)[^\\n]*(scatter|sparse)',
  'why': 'Without it HIP compiles 12 architectures (30-60+ min per package).',
  'fix': 'export PYTORCH_ROCM_ARCH=gfx942 before building.'},
 {'id': 'torch_sparse_plain_gcc',
  'kind': 'forbid',
  'pattern': 'CXX=\\S*(mpic\\+\\+|mpicxx|CC\\b)[^\\n]*(pytorch_sparse|torch_sparse)|(pytorch_sparse|torch_sparse)[^\\n]*CXX=\\S*(mpic\\+\\+|mpicxx)',
  'why': "torch_sparse linked with Cray's OpenMP fails at import: undefined symbol "
         '_cray$mt_kmpc_fork_call_with_flags.',
  'fix': 'module load gcc-native/13; CC=gcc CXX=g++ for torch_sparse.'},
 {'id': 'flux_no_mixed_per_resource_task',
  'kind': 'forbid',
  'pattern': 'flux\\s+(run|submit)[^\\n]*--tasks-per-node[^\\n]*(\\s-g\\s*\\d|--gpus-per-task)|flux\\s+(run|submit)[^\\n]*(\\s-g\\s*\\d|--gpus-per-task)[^\\n]*--tasks-per-node',
  'why': "Per-resource options can't be used with per-task options.",
  'fix': 'flux run -N<nodes> -n<total_tasks> -g<gpus_per_task>.'},
 {'id': 'service_not_flux_run',
  'kind': 'forbid',
  'pattern': 'flux\\s+run[^\\n]*dftracer_service\\s+start',
  'why': 'flux run dftracer_service start never returns; the daemon holds the nodes (2026-07-29).',
  'fix': 'flux submit -N<n> -n<n> -c1 dftracer_service start <dir>, then poll the pid files.'},
 {'id': 'service_no_tasks_per_node',
  'kind': 'forbid',
  'pattern': 'flux\\s+(run|submit)[^\\n]*--tasks-per-node[^\\n]*dftracer_service',
  'why': '--tasks-per-node silently reserves the nodes exclusively, so training cannot co-locate.',
  'fix': 'Use -n<n> -c1.'},
 {'id': 'master_addr_from_nodelist',
  'kind': 'forbid',
  'pattern': 'MASTER_ADDR=(\\$\\(\\s*hostname|\\$HOSTNAME|`hostname|\\$\\(\\s*flux\\s+getattr\\s+local-uri)',
  'why': 'Ranks compute different MASTER_ADDR and the NCCL/RCCL rendezvous hangs silently.',
  'fix': 'MASTER_ADDR=$(flux hostlist -n 0 "$NODELIST") with NODELIST from flux job info $FLUX_JOB_ID R.'},
 {'id': 'python_unbuffered',
  'kind': 'require_if',
  'pattern': 'flux\\s+(run|submit)[^\\n]*\\spython3?\\s+-u\\b',
  'when': 'flux\\s+(run|submit)[^\\n]*\\spython3?\\s',
  'why': 'Buffered stdout makes a slow multi-rank import look like a hang.',
  'fix': 'Launch with python -u.'},
 {'id': 'service_env_exported',
  'kind': 'require_if',
  'pattern': '(?s)(?=.*DFTRACER_ENABLE=)(?=.*DFTRACER_LOG_FILE=)',
  'when': 'dftracer_service\\s+start',
  'why': 'Without DFTRACER_ENABLE and DFTRACER_LOG_FILE the daemon silently no-ops.',
  'fix': 'export DFTRACER_ENABLE=1 DFTRACER_LOG_FILE=<dir>/<prefix> before starting.'},
 {'id': 'ld_preload_modern_libstdcxx',
  'kind': 'forbid',
  'pattern': 'LD_PRELOAD=(?![^\\n]*libstdc\\+\\+\\.so\\.6[^\\n]*libdftracer_preload)[^\\n]*libdftracer_preload',
  'why': 'libdftracer_preload.so pulls the old system libstdc++ (no GLIBCXX_3.4.32), breaking '
         'torch_scatter/torch_sparse imports.',
  'fix': 'LD_PRELOAD=<modern>/libstdc++.so.6:<dftracer_prefix>/lib/libdftracer_preload.so.'}]
