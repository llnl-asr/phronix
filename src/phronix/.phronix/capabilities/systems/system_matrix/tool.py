"""system_matrix: System profile for matrix (LLNL, 4x NVIDIA H100 sm_90 + 2x Xeon 8480+ Sapphire Rapids, TOSS 4, Slurm): the gcc/mvapich2/cuda toolchain that works, pdebug/pci/pbatch limits and backlogs, where CUPTI really lives (not /usr/local/cuda), the 17-preset PAPI ceiling, unreadable CPU power (NVML only), the pip index override, and the Slurm traps (RestrictedCoresPerGPU, DefMemPerCPU, WaitTime=30, MVAPICH MPI interceptors). Load for any dftracer session, build or job launch on matrix, or on 'Invalid generic resource (gres) specification', 'Requested node configuration is not available', 'reserved for jobs in higher priority partitions', a rank OOM-killed ~4 s in, a truncated service_<host>.pfw.gz with step CANCELLED by your own uid, CUDA events with ts == 0, 0 MPIDFTracer::MPI_ symbols, 'Resource deadlock avoided', SIGPIPE rc 141 at the second MPI_Init, pip 'Name or service not known', or dftracer_split 'Device or resource busy' rc 134."""
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


def _SYSTEM_MATRIX_judge(commands, rules):
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
    def system_matrix_recipe(section: str = "") -> str:
        """The build/run/env recipe system_matrix knows, as structured JSON: cuda_cupti, dftracer_source, filesystems, hardware, modules, papi, partitions, permissions, pip, power, slurm, throughput.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (cuda_cupti, dftracer_source, filesystems, hardware, modules, papi, partitions, permissions, pip, power, slurm, throughput); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_matrix_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_MATRIX_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_matrix", "sections": sorted(_SYSTEM_MATRIX_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_MATRIX_RULES]})

    @mcp.tool()
    def system_matrix_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_matrix's rules: no_multinode_pdebug; no_papi_600_module; no_usr_local_cuda; cuda_path_pinned; no_variorum; no_bash_lc_modules; multinode_exclusive_gres; daemon_step_wait0; pip_site_mirror; one_mpi_per_srun; no_pkill_f.

        Use on a proposed recipe or command list before running it, and after system_matrix_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_MATRIX_judge(commands, _SYSTEM_MATRIX_RULES))


_SYSTEM_MATRIX_RECIPE = {'hardware': {'gpus': '4x NVIDIA H100 80GB HBM3, compute capability 9.0 (sm_90)',
              'driver': '610.43.02',
              'cpu': '2x Intel Xeon Platinum 8480+ (Sapphire Rapids)',
              'cores': 112,
              'numa_regions': 8,
              'restricted_cores_per_gpu': 28,
              'memory_gb': 515,
              'os': 'RHEL 8.10 / TOSS 4',
              'scheduler': 'slurm',
              'login_nodes': 'no GPU, no NVIDIA driver - probe on compute nodes via srun'},
 'partitions': {'pdebug': {'max_nodes': 1,
                           'total_nodes': 2,
                           'max_time': '1h',
                           'backlog': 'usually empty',
                           'use': 'every single-node run'},
                'pci': {'max_nodes': 10,
                        'total_nodes': 20,
                        'max_time': '24h',
                        'backlog': 'usually near-idle',
                        'use': 'multi-node work (preferred)',
                        'note': 'nodes are a subset of pbatch'},
                'pbatch': {'max_nodes': 10,
                           'total_nodes': 35,
                           'max_time': '24h',
                           'backlog': 'heavy (177 queued, ~4-day start observed)',
                           'use': 'last resort'},
                'inspect': ['sinfo -o "%20P %5a %10l %6D %10T %N"',
                            "scontrol show partition <name> | tr ' ' '\\n' | grep -E "
                            '"MaxNodes|MaxTime|TotalNodes"'],
                'compare': 'for p in pbatch pci; do sbatch -p $p -N<n> -t <min> --gres=gpu:4 --test-only '
                           '--wrap=hostname; done',
                'backfill': 'driven by node count, insensitive to walltime: request exactly the nodes needed'},
 'modules': {'load_order': ['gcc/12.1.1-magic', 'mvapich2/2.3.7', 'cuda/12.6.0'],
             'how': 'in a sourced script file, then verify with `which` (bash -lc module purge/load rolls back)',
             'env': {'CUDA_HOME': '/usr/tce/packages/cuda/cuda-12.6.0',
                     'CC': '$(command -v mpicc)',
                     'CXX': '$(command -v mpicxx)'},
             'available': {'gcc': '10.3.1-13.3.1',
                           'clang': '14-22',
                           'intel': 'intel / intel-classic',
                           'mpi': ['mvapich2/2.3.6', 'mvapich2/2.3.7', 'openmpi/4.1.2']},
             'mpi_modulefiles': '/usr/tce/modulefiles/MPI/<compiler>/',
             'site_default': 'intel-classic + mvapich2',
             'gcc_limit': 'CUDA 12.6 supports gcc <= 13'},
 'cuda_cupti': {'pin': 'DFTRACER_CUDA_PATH=/usr/tce/packages/cuda/cuda-12.6.0',
                'good_toolkits': ['cuda/11.8.0', 'cuda/12.2.2', 'cuda/12.6.0', 'cuda/12.9.1', 'cuda/13.1.1'],
                'layout': ['<root>/include/cupti.h', '<root>/lib64/libcupti.so'],
                'bad': {'/usr/local/cuda-12.0': 'no CUPTI (no extras/, no include/cupti.h)',
                        'nsight-systems/*/target-linux-x64/libcupti.so.*': 'injection libs, no headers'},
                'permission': 'NVreg_RestrictProfilingToAdminUsers=0 (ordinary user OK); CUPTI_API_VERSION=24'},
 'papi': {'library': '/usr/lib64/libpapi.so.5',
          'version': '5.6.0.0 (LLNL-patched)',
          'hw_counters': 19,
          'presets': 17,
          'fit_at_once': 10,
          'component': 'perf_event (PMUs ix86arch, perf, perf_raw, spr)',
          'disabled': {'rapl': 'CPU model not supported', 'perf_event_uncore': 'needs perf_event_paranoid=0'},
          'no_component': 'CUDA / NVML',
          'bad_module': 'papi/6.0.0.1 (0 counters, 0 presets)',
          'partition_method': 'software_papi'},
 'power': {'cpu': 'unavailable: /dev/cpu/*/msr root-only, msr_safe not loaded; '
                  '/sys/class/powercap/intel-rapl:0/energy_uj mode 0400',
           'gpu': 'NVML works as ordinary user',
           'nvml_query': 'nvidia-smi --query-gpu=index,power.draw,utilization.gpu,memory.used '
                         '--format=csv,noheader,nounits',
           'systems_yaml': 'tracing.power: off (opted_out: True, can_enable: False)',
           'variorum': 'do not build/enable: fatal to dftracer_service',
           'probe_false_positives': ['gpu: rocm_smi (/opt/rocm-7.2.0)', 'cpu: rapl_powercap', 'cpu: msr']},
 'pip': {'env': {'PIP_INDEX_URL': 'https://wci-repo.llnl.gov/repository/pypi-group/simple',
                 'PIP_TRUSTED_HOST': 'wci-repo.llnl.gov',
                 'PIP_EXTRA_INDEX_URL': ''},
         'why': 'pypi.org has no route; user-level ~/.config/pip/pip.conf (NVIDIA PyIndex) overrides /etc/pip.conf'},
 'slurm': {'alloc_single': 'salloc -p pdebug -N1 -t 55 --gres=gpu:4 --no-shell',
           'alloc_multi': 'sbatch --parsable -p pci -N<n> -t <min> --exclusive --gres=gpu:4 --job-name=<name> -o '
                          '<log>/%x_%j.log --wrap "<script>"',
           'step': 'srun --jobid=<J> --overlap -N<n> -n<tasks> --gres=gpu:4 <cmd>',
           'app_step_flags': ['--overlap', '--nodelist=<csv>', '--mem=0', '--kill-on-bad-exit=1', 'outer timeout'],
           'daemon_step_flags': ['--overlap', '--nodelist=<csv>', '--wait=0', '-N<n> -n<n> -c1'],
           'gpu_binding': {'--gres=gpu:4': 'all four GPUs visible to every task',
                           '--gpus-per-task=1': 'one GPU per task, renumbered'},
           'site_config': {'RestrictedCoresPerGPU': 28,
                           'DefMemPerCPU': 4599,
                           'SelectTypeParameters': 'CR_CORE_MEMORY',
                           'WaitTime': 30},
           'one_mpi_per_step': True,
           'sweep_driver': 'one non-blocking sbatch per node scale',
           'test_only': 'sbatch -p <part> -N<n> -t <min> --gres=gpu:4 --test-only --wrap=hostname',
           'shared_nodes_check': 'sinfo -h -p A -o %N ; sinfo -h -p B -o %N',
           'driver_hunt': 'search every login node for /proc/*/cmdline argv[1] == script path; never pkill -f'},
 'filesystems': {'lustre': ['/p/lustre1', '/p/lustre2', '/p/lustre5'],
                 'data_dir': '/p/lustre5/$USER',
                 'workspace': '${WORKSPACE} (NFS): source, builds, venvs, dftracer traces',
                 'layout': 'composite PFL default; use lfs getstripe -d',
                 'split_tmpdir': 'TMPDIR on Lustre for dftracer_split (GENESIS_COMPACT_TMPDIR)'},
 'dftracer_source': {'repo': 'https://github.com/llnl-asr/dftracer',
                     'branch': 'develop',
                     'min_commit_gpu': '324522f (fixed cuda time calculation)',
                     'required_patches': ['MVAPICH MPI interceptor guard fix',
                                          'handle_mpi() self-call recursion fix',
                                          'dftracer_reentry_guard.patch (sysconf/mprotect/madvise/munmap bypass, '
                                          'DFTRACER_TRACE_ALLOC_SYSCALLS=1 opt-in)'],
                     'verify': ["nm -DC libdftracer_core.so | grep -c 'MPIDFTracer::MPI_'  # ~298",
                                "nm -DC libdftracer_core.so | grep -c 'MPIIODFTracer::MPI_'  # ~59"],
                     'ts_check': "sum(1 for e in events if e.get('ts') == 0) == 0"},
 'permissions': {'sudo': False, 'cupti_profiling': 'open', 'perf_event': 'per-process only (no uncore)'},
 'throughput': {'pdebug_single_node': '~5.5 runs/min (miniFE 1-4 ranks, tracing + service + GPU power)'}}

_SYSTEM_MATRIX_RULES = [{'id': 'no_multinode_pdebug',
  'kind': 'forbid',
  'pattern': '(?=.*(-p\\s*|--partition[= ])pdebug\\b)(?=.*(-N\\s*|--nodes[= ])([2-9]|[1-9]\\d))',
  'why': 'matrix pdebug is MaxNodes=1; multi-node requests fail with misleading gres / node-configuration errors.',
  'fix': 'Use -p pci for multi-node work; keep pdebug for N=1.'},
 {'id': 'no_papi_600_module',
  'kind': 'forbid',
  'pattern': 'module\\s+(load|add|swap)\\b.*papi/6\\.0\\.0\\.1',
  'why': 'papi/6.0.0.1 reports 0 counters and 0 presets on Sapphire Rapids.',
  'fix': 'Use the system PAPI /usr/lib64/libpapi.so.5 (5.6.0.0); load no papi module.'},
 {'id': 'no_usr_local_cuda',
  'kind': 'forbid',
  'pattern': '(DFTRACER_CUDA_PATH|CUDA_HOME|CUDA_PATH|CUDAToolkit_ROOT)=\\S*/usr/local/cuda',
  'why': '/usr/local/cuda-12.0 has no CUPTI, so GPU tracing is silently disabled.',
  'fix': 'Point it at /usr/tce/packages/cuda/cuda-12.6.0.'},
 {'id': 'cuda_path_pinned',
  'kind': 'require_if',
  'pattern': 'DFTRACER_CUDA_PATH=\\S*/usr/tce/packages/cuda/cuda-\\d',
  'when': 'DFTRACER_ENABLE_CUDA_TRACING|cupti|DFTRACER_BUILD_CUDA|-DDFTRACER_ENABLE_CUDA',
  'flags': 'i',
  'why': 'Toolkit auto-detect finds the CUPTI-less /usr/local/cuda.',
  'fix': 'export DFTRACER_CUDA_PATH=/usr/tce/packages/cuda/cuda-12.6.0.'},
 {'id': 'no_variorum',
  'kind': 'forbid',
  'pattern': 'DFTRACER_BUILD_VARIORUM=(ALWAYS|ON|1|TRUE|YES)\\b',
  'flags': 'i',
  'why': 'CPU power is unreadable on matrix and variorum init kills dftracer_service.',
  'fix': 'Leave variorum off (DFTRACER_BUILD_VARIORUM=OFF) and use NVML for GPU power.'},
 {'id': 'no_bash_lc_modules',
  'kind': 'forbid',
  'pattern': 'bash\\s+-l?c\\s+[\\"\'][^\\"\']*module\\s+(purge|load)',
  'why': "module purge/load inside bash -lc silently rolls back to the login profile's modules.",
  'fix': 'Put module loads in a sourced script and verify with which.'},
 {'id': 'multinode_exclusive_gres',
  'kind': 'require_if',
  'pattern': '(sbatch|salloc)\\b[^\\n]*--exclusive[^\\n]*--gres=gpu:4|(sbatch|salloc)\\b[^\\n]*--gres=gpu:4[^\\n]*--exclusive',
  'when': '(sbatch|salloc)\\b[^\\n]*(-N\\s*|--nodes[= ])([2-9]|[1-9]\\d)',
  'why': 'RestrictedCoresPerGPU=28: without GPUs a job gets 28 of 112 cores and subset steps fail with a gres error.',
  'fix': 'Allocate multi-node jobs with --exclusive --gres=gpu:4 (even CPU-only).'},
 {'id': 'daemon_step_wait0',
  'kind': 'require_if',
  'pattern': 'srun\\b[^\\n]*--wait=0[^\\n]*dftracer_service',
  'when': 'srun\\b[^\\n]*dftracer_service',
  'why': "WaitTime=30 SIGKILLs the slower node's daemon mid-flush 30 s after the first exits.",
  'fix': 'Add --wait=0 (and --overlap --nodelist) to the daemon srun step.'},
 {'id': 'pip_site_mirror',
  'kind': 'require_if',
  'pattern': 'PIP_INDEX_URL=https://wci-repo\\.llnl\\.gov',
  'when': '\\bpip3?\\s+install\\b',
  'why': 'pypi.org is unroutable and a user-level pip.conf overrides the site mirror.',
  'fix': 'export PIP_INDEX_URL=https://wci-repo.llnl.gov/repository/pypi-group/simple '
         'PIP_TRUSTED_HOST=wci-repo.llnl.gov PIP_EXTRA_INDEX_URL='},
 {'id': 'one_mpi_per_srun',
  'kind': 'forbid',
  'pattern': 'srun\\b.*\\bbash\\s+-c\\s+[\\"\']?\\s*for\\b',
  'why': 'A second MPI_Init in the same srun step dies with SIGPIPE rc 141.',
  'fix': 'Issue one srun per MPI run.'},
 {'id': 'no_pkill_f',
  'kind': 'forbid',
  'pattern': '\\bpkill\\s+(-\\w+\\s+)*-f\\b',
  'why': 'pkill -f also matches (and kills) the monitoring shell; a driver on another login node survives it.',
  'fix': 'Match /proc/*/cmdline argv[1] == script path on every login node; confirm by the log stopping.'}]
