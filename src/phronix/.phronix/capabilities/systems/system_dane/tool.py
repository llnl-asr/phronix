"""system_dane: System profile for dane (LLNL CTS-2, 2x Xeon 8480+ Sapphire Rapids, 112 cores, NO GPU, TOSS 4, Slurm): the bank check that gates every job, the 1440-node pbatch/pci pool, multi-node pdebug (MaxNodes=20), 7-day single-node pserial, the gcc/mvapich2 toolchain, the 17-preset system PAPI (papi/6.0.0.1 useless), zero readable power, no /p/lustre5, and the two false-positive GPU signals (nvidia-smi present, full /opt/rocm-6.4.3 and 7.2.0 trees). Load for any dftracer session, build or job launch on dane, or on 'allocation failure: Invalid account or account/partition combination specified', nvidia-smi 'couldn't communicate with the NVIDIA driver', a probe reporting an AMD/NVIDIA GPU or rocm_smi power on dane, a dangling dataset symlink / 'no result file' audit, or a ppn ladder sized off lscpu's 224 CPUs."""
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


def _SYSTEM_DANE_judge(commands, rules):
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
    def system_dane_recipe(section: str = "") -> str:
        """The build/run/env recipe system_dane knows, as structured JSON: bank_check, false_gpu_signals, filesystems, hardware, launcher, modules, network, papi, partitions, permissions, power, transfers, verification_status.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (bank_check, false_gpu_signals, filesystems, hardware, launcher, modules, network, papi, partitions, permissions, power, transfers, verification_status); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_dane_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_DANE_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_dane", "sections": sorted(_SYSTEM_DANE_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_DANE_RULES]})

    @mcp.tool()
    def system_dane_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_dane's rules: no_gpu_tracing; no_papi_600_module; no_pall; pserial_single_node; pdebug_max20; no_lustre5; no_flux; ppn_max_112; no_variorum_power; bank_check_first.

        Use on a proposed recipe or command list before running it, and after system_dane_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_DANE_judge(commands, _SYSTEM_DANE_RULES))


_SYSTEM_DANE_RECIPE = {'bank_check': {'commands': ['sacctmgr -nP show assoc user=$USER cluster=dane format=Account,Partition,QOS',
                             'sshare -U -u $USER'],
                'empty_means': 'no bank: every submission fails; stop and request one from the project coordinator',
                'error': 'allocation failure: Invalid account or account/partition combination specified'},
 'hardware': {'gpus': 'none',
              'cpu': '2x Intel Xeon Platinum 8480+ (Sapphire Rapids), 3.8 GHz max',
              'cores_online': 112,
              'smt': 'off',
              'lscpu_cpus_misleading': 224,
              'numa_regions': '8 (SNC-4 per socket)',
              'l3_mb': 107,
              'memory_gb': 251,
              'os': 'RHEL 8.10 / TOSS 4 (toss-release-4.8)',
              'scheduler': 'slurm 25.11.7',
              'nodes': '~1500',
              'papi_sockets_reported': '4 (SNC domains, not packages)'},
 'false_gpu_signals': {'nvidia_smi': "/usr/bin/nvidia-smi exists, fails: couldn't communicate with the NVIDIA driver",
                       'rocm': '8 /opt/rocm-* trees (5.4.3..5.7.1 llvm-only stubs; 6.4.3 and 7.2.0 complete)',
                       'truth': 'lspci shows no display/3D controller',
                       'never_set': ['DFTRACER_ENABLE_HIP_TRACING', 'DFTRACER_ENABLE_CUDA_TRACING']},
 'partitions': {'pbatch': {'default': True,
                           'nodes': 1440,
                           'max_nodes': 520,
                           'max_time': '24h',
                           'observed_backlog': '~5285 queued'},
                'pci': {'qos': 'ci_dane',
                        'nodes': 1440,
                        'max_nodes': 520,
                        'max_time': '24h',
                        'observed_backlog': '~7 queued',
                        'prefer': True},
                'pdebug': {'nodes': 38,
                           'max_nodes': 20,
                           'max_time': '1h',
                           'observed_backlog': '~36 queued',
                           'use': '1->2->4->8->16 node ladders of short runs'},
                'pserial': {'nodes': 16,
                            'max_nodes': 1,
                            'max_time': '7 days',
                            'observed_backlog': '~1546 queued',
                            'use': 'long single-node work only'},
                'pjupyter': {'nodes': 2, 'max_nodes': 1, 'max_time': '24h'},
                'pall': {'nodes': 1496, 'state': 'DOWN', 'use': 'never'},
                'inspect': 'scontrol show partition <name> (MaxNodes not in default sinfo)',
                'shape_probe': 'for p in pdebug pci pbatch; do sbatch -p $p -N8 -t 60 --test-only --wrap=hostname '
                               '2>&1 | tail -1; done'},
 'modules': {'site_default': ['intel-classic/2021.6.0-magic', 'mvapich2/2.3.7'],
             'load_order': ['gcc/12.1.1-magic', 'mvapich2/2.3.7'],
             'env': {'CC': '$(command -v mpicc)', 'CXX': '$(command -v mpicxx)'},
             'available': {'gcc': '10.3.1-13.3.1',
                           'clang': '14-22',
                           'intel': 'intel / intel-classic 19.0-2025.3',
                           'mpi': ['mvapich2/2.3.6', 'mvapich2/2.3.7', 'openmpi/4.1.2'],
                           'cmake': '<= 3.30.5',
                           'other': ['meson',
                                     'ninja',
                                     'mpifileutils/0.12',
                                     'patchelf',
                                     'python 3.9-3.14',
                                     'hpctoolkit',
                                     'vtune',
                                     'valgrind'],
                           'compile_only': ['cuda/10.1 .. cuda/13.1.1', 'nsight', 'nvidia/375']},
             'mpi_modulefiles': '/usr/tce/modulefiles/MPI/<compiler>/',
             'bash_lc': 'module purge && module load inside bash -lc survives here (unlike matrix)',
             'do_not_load': ['papi/6.0.0.1']},
 'papi': {'library': '/usr/lib64/libpapi.so.5',
          'version': '5.6.0.0 (LLNL-patched)',
          'tools': '/usr/bin/papi_avail, papi_component_avail',
          'hw_counters': 19,
          'presets': 17,
          'native': ['PAPI_TOT_INS',
                     'PAPI_TOT_CYC',
                     'PAPI_REF_CYC',
                     'PAPI_BR_INS',
                     'PAPI_BR_CN',
                     'PAPI_BR_TKN',
                     'PAPI_BR_NTK',
                     'PAPI_BR_MSP'],
          'derived': ['PAPI_BR_UCN',
                      'PAPI_BR_PRC',
                      'PAPI_FP_INS',
                      'PAPI_VEC_INS',
                      'PAPI_FP_OPS',
                      'PAPI_SP_OPS',
                      'PAPI_DP_OPS',
                      'PAPI_VEC_SP',
                      'PAPI_VEC_DP'],
          'component': 'perf_event (PMUs ix86arch, perf, perf_raw, spr)',
          'disabled': {'rapl': 'CPU model not supported', 'perf_event_uncore': 'perf_event_paranoid is 1, needs 0'},
          'systems_yaml': 'tracing.papi_module: ""',
          'partition_method': 'software_papi (same CPU as matrix)'},
 'power': {'msr': '/dev/cpu/*/msr crw------- root, msr_safe not loaded',
           'rapl_sysfs': 'energy_uj mode 0400 root-owned',
           'papi_rapl': 'disabled',
           'gpu': 'none',
           'systems_yaml': 'tracing.power: off',
           'env': {'DFTRACER_DISABLE_VARIORUM_POWER': '1'},
           'expect': 'zero power events; state it in the corpus README',
           'variorum_hazard': 'cores(1) mod sockets(2) != 0 -> exit() kills dftracer_service'},
 'filesystems': {'lustre': {'/p/lustre1': '24 PB o2ib600',
                            '/p/lustre2': '24 PB o2ib600',
                            '/p/lustre3': '8 PB o2ib100'},
                 'vast': '/p/vast1 (11 PB, ~80% full)',
                 'data_dir': '/p/lustre1/$USER',
                 'workspace': '${WORKSPACE} (NFS): source, builds, venvs, dftracer traces',
                 'missing': '/p/lustre5 (exists on tuolumne/matrix only)',
                 'dataset_check': 'readlink -f ${SESSION}/dataset && test -d ${SESSION}/dataset && echo RESOLVES || '
                                  'echo DANGLES'},
 'network': {'pip': '/etc/pip.conf -> https://wci-repo.llnl.gov/repository/pypi-group/simple; no user-level '
                    'override; pypi.org routes',
             'czgitlab': 'SSH :7999 open; HTTPS not'},
 'launcher': {'type': 'srun',
              'workflow': 'software_slurm_alloc',
              'pdebug_ladder': 'salloc -p pdebug -N<1..16> -t 60'},
 'permissions': {'sudo': False, 'perf_event_paranoid': 1},
 'transfers': {'from_matrix_ok': ['PAPI ceiling/partition',
                                  'CPU power unreadable (no NVML fallback here)',
                                  'Slurm --overlap/--nodelist'],
               'from_matrix_partial': ['pip Nexus mirror (no user-conf override here)'],
               'do_not_transfer': ['matrix pdebug MaxNodes=1',
                                   'bash -lc module rollback',
                                   'CUDA/CUPTI',
                                   'ROCm/HIP',
                                   'Flux',
                                   '/p/lustre5']},
 'verification_status': 'login-node measurements only (2026-08-27); compute-node PAPI and ppn ladder pending a bank'}

_SYSTEM_DANE_RULES = [{'id': 'no_gpu_tracing',
  'kind': 'forbid',
  'pattern': 'DFTRACER_ENABLE_(HIP|CUDA)_TRACING\\s*=\\s*(1|ON|TRUE|YES)\\b',
  'flags': 'i',
  'why': 'dane has no GPU; nvidia-smi and /opt/rocm-* are false positives.',
  'fix': 'Drop GPU tracing on dane.'},
 {'id': 'no_papi_600_module',
  'kind': 'forbid',
  'pattern': 'module\\s+(load|add|swap)\\b.*papi/6\\.0\\.0\\.1',
  'why': 'papi/6.0.0.1 reports 0 counters and 0 presets on Sapphire Rapids.',
  'fix': 'Use the system PAPI /usr/lib64/libpapi.so.5; load no papi module.'},
 {'id': 'no_pall',
  'kind': 'forbid',
  'pattern': '(-p\\s*|--partition[= ])pall\\b',
  'why': 'pall is State=DOWN on dane.',
  'fix': 'Use pci (multi-node) or pdebug (<= 20 nodes, 1 h).'},
 {'id': 'pserial_single_node',
  'kind': 'forbid',
  'pattern': '(?=.*(-p\\s*|--partition[= ])pserial\\b)(?=.*(-N\\s*|--nodes[= ])([2-9]|[1-9]\\d))',
  'why': 'pserial is MaxNodes=1.',
  'fix': 'Use pserial only for 1-node long runs; scale on pdebug/pci.'},
 {'id': 'pdebug_max20',
  'kind': 'forbid',
  'pattern': '(?=.*(-p\\s*|--partition[= ])pdebug\\b)(?=.*(-N\\s*|--nodes[= ])(2[1-9]|[3-9]\\d|\\d{3,}))',
  'why': 'dane pdebug is MaxNodes=20.',
  'fix': 'Use pci for > 20 nodes.'},
 {'id': 'no_lustre5',
  'kind': 'forbid',
  'pattern': '/p/lustre5\\b',
  'why': 'dane does not mount /p/lustre5; symlinks onto it dangle and the app silently writes nothing.',
  'fix': 'Use /p/lustre1..3 (e.g. /p/lustre1/$USER).'},
 {'id': 'no_flux',
  'kind': 'forbid',
  'pattern': '^\\s*flux\\s+(alloc|run|submit|proxy|batch)\\b',
  'why': 'dane runs Slurm, not Flux.',
  'fix': 'Use salloc/sbatch/srun (software_slurm_alloc).'},
 {'id': 'ppn_max_112',
  'kind': 'forbid',
  'pattern': '(--ntasks-per-node[= ]\\s*|ppn=)(11[3-9]|1[2-9]\\d|[2-9]\\d\\d)\\b',
  'why': "Only 112 cores are online (lscpu's 224 counts offline SMT siblings).",
  'fix': 'Cap ranks per node at nproc = 112.'},
 {'id': 'no_variorum_power',
  'kind': 'require_if',
  'pattern': 'DFTRACER_DISABLE_VARIORUM_POWER=1',
  'when': 'dftracer_service|DFTRACER_ENABLE=1|libdftracer',
  'why': 'No power source is readable and variorum init kills dftracer_service on a 2-socket node.',
  'fix': 'export DFTRACER_DISABLE_VARIORUM_POWER=1.'},
 {'id': 'bank_check_first',
  'kind': 'require_if',
  'pattern': 'sacctmgr\\b.*cluster=dane|sshare\\s+-U',
  'when': '(^|\\n)\\s*(sbatch|salloc)\\b',
  'why': 'Without a bank every submission fails with a message that looks like a partition problem.',
  'fix': 'Run sacctmgr -nP show assoc user=$USER cluster=dane ... first.'}]
