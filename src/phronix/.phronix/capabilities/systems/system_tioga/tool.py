"""system_tioga: System profile for tioga (LLNL Cray EX, AMD MI250X gfx90a, 8 GCDs/node, EPYC 7A53 Trento 64 cores, Flux): same software stack as Tuolumne (rocm/6.4.2, rocmcc/6.4.2-cce-20.0.0-magic, cray-mpich/9.0.1, papi/7.2.0.2; binaries portable) but different hardware, queues, PAPI presets and Lustre. Load for any dftracer session, build or job launch on tioga, or when a job sits in S forever (pall scheduling stopped, drained nodes, cores exhausted by dftracer_service), on 'flux-alloc: ERROR: queue "pllm" not valid for user', a gfx942 binary whose kernels do not run, missing PAPI_L2_TCM / PAPI_L2_TCH / PAPI_FMA_INS, a multi-rank traced GPU run SIGSEGV at >= 3 ranks, zero variorum power events, 'corrupted size vs. prev_size in fastbins' at service teardown, or a dangling /p/lustre5 dataset symlink."""
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


def _SYSTEM_TIOGA_judge(commands, rules):
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
    def system_tioga_recipe(section: str = "") -> str:
        """The build/run/env recipe system_tioga knows, as structured JSON: build, carries_over_from_tuolumne, cores_per_rank, dftracer_service, filesystems, gpu_profiling, hardware, modules, papi, queues.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (build, carries_over_from_tuolumne, cores_per_rank, dftracer_service, filesystems, gpu_profiling, hardware, modules, papi, queues); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_tioga_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_TIOGA_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_tioga", "sections": sorted(_SYSTEM_TIOGA_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_TIOGA_RULES]})

    @mcp.tool()
    def system_tioga_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_tioga's rules: no_pall_queue; no_gfx942; pdebug_max8; no_variorum_auto; service_start_via_submit; service_hosts_pinned; no_lustre5; no_tuolumne_only_presets; queue_status_checked; resource_list_checked.

        Use on a proposed recipe or command list before running it, and after system_tioga_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_TIOGA_judge(commands, _SYSTEM_TIOGA_RULES))


_SYSTEM_TIOGA_RECIPE = {'hardware': {'gpu': 'AMD MI250X, gfx90a, discrete',
              'gpus_per_node': '8 GCDs',
              'cpu': 'AMD EPYC 7A53 (Trento), 64 cores / 128 threads',
              'numa_domains': 4,
              'craype_arch': 'craype-x86-trento',
              'gpu_ppn_ladder': [1, 2, 4, 8],
              'offload_arch': 'gfx90a',
              'vs_tuolumne': {'gpu': 'MI300A APU gfx942', 'gpus_per_node': 4, 'cores': 96}},
 'queues': {'pdebug': {'default': True,
                       'nodes': 8,
                       'time_limit': '12h',
                       'note': 'workhorse; whole sweep usually fits one allocation'},
            'pllm': {'nodes': 18, 'time_limit': '1d', 'note': 'often not authorized for the account'},
            'pci': {'nodes': 4, 'time_limit': '2h'},
            'pall': {'nodes': 30, 'time_limit': '1d', 'note': 'scheduling stopped - never use'},
            'preflight_order': ['flux queue list',
                                'flux queue status',
                                'flux resource list',
                                'throwaway flux alloc (authorization)'],
            'sizing': 'size to free nodes from flux resource list, not advertised maximum; stop if the largest cells '
                      'cannot fit',
            'auth_error': 'flux-alloc: ERROR: queue "pllm" not valid for user; valid queues for user: pdebug,pci'},
 'modules': {'pins': ['rocm/6.4.2', 'rocmcc/6.4.2-cce-20.0.0-magic', 'cray-mpich/9.0.1', 'papi/7.2.0.2'],
             'also_present': ['papi/7.3.0.1 (probe before trusting)', 'rocm up to 7.2.1'],
             'default_env': ['PrgEnv-cray/8.7.0', 'cce/20.0.0']},
 'cores_per_rank': {'cores_per_node': 64,
                    'reserved_for_dftracer_service': 1,
                    'formula': 'floor((cores_per_node - 1) / max_ppn)',
                    'measured': {'ppn8_c8': 'never schedules', 'ppn8_c7': 'works'}},
 'papi': {'hw_counters': 5,
          'presets': 27,
          'derived': ['PAPI_TLB_IM', 'PAPI_BR_UCN', 'PAPI_BR_TKN', 'PAPI_BR_NTK', 'PAPI_BR_PRC'],
          'available': ['PAPI_BR_CN',
                        'PAPI_BR_INS',
                        'PAPI_BR_MSP',
                        'PAPI_BR_NTK',
                        'PAPI_BR_PRC',
                        'PAPI_BR_TKN',
                        'PAPI_BR_UCN',
                        'PAPI_FAD_INS',
                        'PAPI_FDV_INS',
                        'PAPI_FML_INS',
                        'PAPI_FP_INS',
                        'PAPI_FP_OPS',
                        'PAPI_FSQ_INS',
                        'PAPI_L1_DCA',
                        'PAPI_L1_DCM',
                        'PAPI_L2_DCH',
                        'PAPI_L2_DCM',
                        'PAPI_L2_DCR',
                        'PAPI_L2_ICA',
                        'PAPI_L2_ICH',
                        'PAPI_L2_ICM',
                        'PAPI_L2_ICR',
                        'PAPI_TLB_DM',
                        'PAPI_TLB_IM',
                        'PAPI_TOT_CYC',
                        'PAPI_TOT_INS',
                        'PAPI_VEC_INS'],
          'missing_vs_tuolumne': ['PAPI_L2_TCM', 'PAPI_L2_TCH', 'PAPI_FMA_INS'],
          'native_here_derived_on_tuolumne': ['PAPI_L2_ICM',
                                              'PAPI_FP_INS',
                                              'PAPI_FML_INS',
                                              'PAPI_FAD_INS',
                                              'PAPI_FDV_INS',
                                              'PAPI_FSQ_INS'],
          'tuolumne': {'presets': 30, 'derived': 12},
          'method': 'derive from papi_avail, probe args.multiplex == 0 (software_papi)',
          'version': {'safe': 'papi/7.2.0.2',
                      'unverified': 'papi/7.3.0.1 (SIGSEGVs on Tuolumne with ROCm 6.4.2 via rocp_sdk)'}},
 'filesystems': {'lustre': ['/p/lustre1 (main, ~24 PB)', '/p/lustre2 (writable, ~24 PB)'],
                 'data_dir': '/p/lustre1/$USER',
                 'not_mounted': '/p/lustre5 (Tuolumne)',
                 'workspace': '${WORKSPACE} (NFS, shared with Tuolumne)',
                 'traces': 'session workspace genesis_traces/, never Lustre',
                 'check': 'ls -d /p/lustre*'},
 'dftracer_service': {'start': 'flux submit -N<n> --requires=host:<hosts> dftracer_service start (detached; poll '
                               'per-host pid files)',
                      'app': 'flux run -N<n> --requires=host:<hosts> -c <cores_per_rank> <app>',
                      'stop': 'flux run -N<n> --requires=host:<hosts> dftracer_service stop',
                      'teardown_abort': 'corrupted size vs. prev_size in fastbins (post-flush, harmless)'},
 'build': {'cmake_flags': ['-DDFTRACER_BUILD_VARIORUM=ALWAYS', '-DCMAKE_HIP_ARCHITECTURES=gfx90a'],
           'required_fix': 'BufferManager ready atomic (>= 3-rank traced GPU init SIGSEGV)',
           'verify': 'a gpu/power event lands in the trace'},
 'gpu_profiling': {'activity_tracing': 'works (kernel dispatch, memory copy, page migration)',
                   'hw_counters': 'unavailable (no SYS_PERFMON)'},
 'carries_over_from_tuolumne': ['service start via flux submit',
                                '--requires=host: pinning',
                                'VARIORUM=ALWAYS',
                                'librocm_smi64 double ABI teardown abort',
                                'ROCProfiler SYS_PERFMON warning']}

_SYSTEM_TIOGA_RULES = [{'id': 'no_pall_queue',
  'kind': 'forbid',
  'pattern': '(-q\\s*|--queue[= ])pall\\b',
  'why': 'pall accepts jobs but its scheduling is stopped; they sit S forever.',
  'fix': 'Use -q pdebug (8 nodes, 12 h).'},
 {'id': 'no_gfx942',
  'kind': 'forbid',
  'pattern': 'gfx942',
  'why': 'tioga MI250X is gfx90a; gfx942 kernels will not run.',
  'fix': 'Target gfx90a.'},
 {'id': 'pdebug_max8',
  'kind': 'forbid',
  'pattern': '(?=.*(-q\\s*|--queue[= ])pdebug\\b)(?=.*(-N\\s*|--nodes[= ])(9|[1-9]\\d))',
  'why': 'tioga pdebug has 8 nodes (often only a few free).',
  'fix': 'Size to free nodes from flux resource list (<= 8).'},
 {'id': 'no_variorum_auto',
  'kind': 'forbid',
  'pattern': 'DFTRACER_BUILD_VARIORUM=AUTO\\b',
  'flags': 'i',
  'why': 'AUTO finds the system variorum RPM that yields zero power events.',
  'fix': 'Use DFTRACER_BUILD_VARIORUM=ALWAYS and verify a power event lands.'},
 {'id': 'service_start_via_submit',
  'kind': 'forbid',
  'pattern': 'flux\\s+run\\b.*dftracer_service\\s+start',
  'why': 'dftracer_service start under flux run never returns.',
  'fix': 'flux submit it detached and poll per-host pid files.'},
 {'id': 'service_hosts_pinned',
  'kind': 'require_if',
  'pattern': '--requires=host:',
  'when': 'dftracer_service',
  'why': 'In a larger allocation, service start, app and stop otherwise land on different node subsets.',
  'fix': 'Pin all three with --requires=host:<hosts>.'},
 {'id': 'no_lustre5',
  'kind': 'forbid',
  'pattern': '/p/lustre5\\b',
  'why': 'tioga mounts /p/lustre1 and /p/lustre2 only; /p/lustre5 symlinks dangle.',
  'fix': 'Use /p/lustre1/$USER.'},
 {'id': 'no_tuolumne_only_presets',
  'kind': 'forbid',
  'pattern': 'PAPI_(L2_TCM|L2_TCH|FMA_INS)\\b',
  'why': 'These presets exist on Tuolumne but not on tioga.',
  'fix': "Re-derive the counter set from tioga's papi_avail."},
 {'id': 'queue_status_checked',
  'kind': 'require_if',
  'pattern': 'flux\\s+queue\\s+status',
  'when': 'flux\\s+(alloc|batch)\\b',
  'why': "flux queue list hides that pall's scheduler is stopped.",
  'fix': 'Run flux queue status (and flux resource list) before allocating.'},
 {'id': 'resource_list_checked',
  'kind': 'require_if',
  'pattern': 'flux\\s+resource\\s+list',
  'when': 'flux\\s+(alloc|batch)\\b',
  'why': 'Queue node counts are advertised, not free; many nodes are drained.',
  'fix': 'Run flux resource list and size to free nodes.'}]
