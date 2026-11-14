"""software_rocm: ROCm / HIP / rocprofiler-sdk knowledge for dftracer HIP tracing on AMD GPUs (MI300A): the strict init ordering rocprofiler_force_configure needs (import torch before initialize_log, before touching the GPU), building DFTRACER_ENABLE_HIP_TRACING against a ROCm >= 6.2 prefix on CMAKE_PREFIX_PATH (else it silently compiles out), PyTorch-profiler coexistence for exactly one profiler window, ROCm base-vs-patched tree matching with the torch wheel, MI300A unified-memory scope, XLA preallocation on APUs, RCCL transport (rccl/working-env, aws-ofi-rccl on LD_LIBRARY_PATH, never guess NCCL_NET), the DDP fork-bomb on non-exclusive flux run, and the HIP-tracing observer effect. Load for any DFTRACER_ENABLE_HIP_TRACING session or ROCm/HIP/RCCL build or run issue, or on: 'Error Calling hsa_iterate_agents: HSA_STATUS_ERROR_NOT_INITIALIZED', "Check failed: '_v' Must be non nullptr", zero HIP_RUNTIME_API/KERNEL_DISPATCH events, 'Memory access fault by GPU node-N ... Reason: Unknown', RCCL hangs or slow host-TCP collectives, Ray TrainingFailedError at a profiler cycle boundary."""
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


def _SOFTWARE_ROCM_judge(commands, rules):
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
    def software_rocm_recipe(section: str = "") -> str:
        """The build/run/env recipe software_rocm knows, as structured JSON: ddp_under_flux, hip_tracing_build, init_order, jax_apu, mi300a_memory, observer_effect, rccl, rocm_tree_matching, torch_profiler, tuning_levers_mi300a_2026_08_05.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (ddp_under_flux, hip_tracing_build, init_order, jax_apu, mi300a_memory, observer_effect, rccl, rocm_tree_matching, torch_profiler, tuning_levers_mi300a_2026_08_05); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_rocm_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_ROCM_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_rocm", "sections": sorted(_SOFTWARE_ROCM_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_ROCM_RULES]})

    @mcp.tool()
    def software_rocm_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_rocm's rules: hip_tracing_needs_rocm_prefix; no_nccl_net_guess; torch_profiler_single_window; torch_profiler_record_shapes; rccl_working_env; rccl_plugin_on_ld_library_path; flux_ddp_exclusive; no_hsa_interrupt_off; no_rocm_smi_perflevel.

        Use on a proposed recipe or command list before running it, and after software_rocm_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_ROCM_judge(commands, _SOFTWARE_ROCM_RULES))


_SOFTWARE_ROCM_RECIPE = {'hip_tracing_build': {'option': 'DFTRACER_ENABLE_HIP_TRACING=ON (compile-time only)',
                       'rocm_min': '6.2',
                       'env': {'ROCM_PATH': '<rocm-prefix>',
                               'HIP_PATH': '<rocm-prefix>',
                               'CMAKE_PREFIX_PATH': 'append <rocm-prefix> (do not overwrite; HDF5 prefix may be '
                                                    'there)'},
                       'failure_mode': 'find_package(rocprofiler-sdk) fails silently -> HIP tracing compiled out, '
                                       'build reports success',
                       'verify': 'real GPU run: HIP_RUNTIME_API and KERNEL_DISPATCH categories non-empty'},
 'init_order': {'window': 'after HSA/HIP shared libs loaded, before hsa_init()',
                'sequence': ['import torch (module load only)', 'dftracer.initialize_log()', 'first GPU touch'],
                'bisect_mi300a_rocm_6_2_4': {'A_no_torch': 'SIGABRT hsa_iterate_agents '
                                                           "HSA_STATUS_ERROR_NOT_INITIALIZED, Check failed '_v'",
                                             'B_A_plus_HIP_VISIBLE_DEVICES': 'same SIGABRT',
                                             'C_torch_touch_gpu_then_init': 'no crash, zero HIP events (silently '
                                                                            'locked)',
                                             'D_import_dftracer_first_then_C': 'same silent no-op',
                                             'E_import_torch_init_then_touch': 'works: HIP_RUNTIME_API, '
                                                                               'KERNEL_DISPATCH, MEMORY_COPY, '
                                                                               'SCRATCH_MEMORY'},
                'entry_points_not_owned': 'sitecustomize.py on PYTHONPATH importing torch when DFTRACER_ENABLE == '
                                          "'1' (e.g. Ray default_worker.py)"},
 'torch_profiler': {'handler': 'dftracer.python.torch.trace_handler (pydftracer develop), cat=PP, anchored on kineto '
                               'trace_start_ns',
                    'required': {'record_shapes': True},
                    'recommended': {'profile_memory': True, 'with_stack': False},
                    'activity_on_rocm': 'ProfilerActivity.CUDA',
                    'schedule_safe': 'schedule(wait=2, warmup=1, active=5, repeat=1)',
                    'schedule_aborts': 'repeat >= 2 (second cycle re-arms roctracer)',
                    'schedule_untested': 'schedule(wait=0, warmup=0, active=K, repeat=0)',
                    'teardown': 'stop profiler before dftracer.finalize()'},
 'rocm_tree_matching': {'rule': 'dftracer and torch +rocm wheel built against the same tree (base or patched)',
                        'patched_variants': ['hangfix', 'leakfix', 'cgroupfix'],
                        'no_patched_example': 'rocm/7.1.1 with torch +rocm710 (Tuolumne)'},
 'mi300a_memory': {'unified_scope': "intra-package (one APU's CPU + GPU XCDs share its HBM); inter-APU = Infinity "
                                    'Fabric transfer',
                   'gpu_addressable': ['hipMalloc', 'hipMallocManaged', 'hipHostMalloc', 'hipHostRegister'],
                   'hint_only': 'hipMemAdvise',
                   'zero_copy_choice': 'hipMallocManaged',
                   'refs': ['Bertolli et al., SC24-W', 'Kuncham, Zhang & Panda, IPDPS 2026, One Memory-Many Paths']},
 'jax_apu': {'XLA_PYTHON_CLIENT_PREALLOCATE': 'false (measured -77% peak mem, -4.9% wall, 2026-08-02)',
             'XLA_PYTHON_CLIENT_MEM_FRACTION': 'unmeasured secondary candidate'},
 'rccl': {'module': 'rccl/working-env (required multi-node)',
          'load_bearing_env': {'FI_MR_CACHE_MONITOR': 'userfaultfd'},
          'plugin': 'aws-ofi-rccl lib dir on LD_LIBRARY_PATH',
          'NCCL_NET': "leave unset (plugin registers as 'AWS Libfabric')",
          'fallback_symptom': 'host TCP sockets, 40%+ wall time, no warnings',
          'ab_validity': 'verify actual transport before comparing gloo vs nccl/rccl'},
 'ddp_under_flux': {'flag': '--exclusive',
                    'unset': ['PMI_RANK',
                              'PMI_SIZE',
                              'PMI_FD',
                              'PALS_APID',
                              'PALS_APINFO',
                              'PALS_NODEID',
                              'PALS_RANKID',
                              'PALS_SPOOL_DIR',
                              'LDCS_RANKINFO'],
                    'see': 'software_flux'},
 'observer_effect': {'inflation': '6.1x-6.7x on launch/sync-heavy kernels (RAJAPerf, MI300A gfx942, ROCm 7.2.1)',
                     'example': '0.960 s traced vs 0.144 s untraced p50',
                     'rule': 'size launch-overhead bottlenecks untraced'},
 'tuning_levers_mi300a_2026_08_05': {'HSA_ENABLE_INTERRUPT=0': 'regression on mixed CPU+GPU (+3.78% net)',
                                     'rocm-smi --setperflevel high': 'admin-gated, not tunable',
                                     'miopen_find_mode': 'n/a for apps with own HIP kernels',
                                     'numa_gpu_affinity': 'confirmed no-op (4 workload classes)',
                                     'hip_graphs': 'live candidate for many-small-launch apps (Ekelund et al. 2025, '
                                                   'arXiv 2501.09398)'}}

_SOFTWARE_ROCM_RULES = [{'id': 'hip_tracing_needs_rocm_prefix',
  'kind': 'require_if',
  'pattern': 'CMAKE_PREFIX_PATH=\\S*(\\$\\{?ROCM_PATH|/opt/rocm)',
  'when': 'DFTRACER_ENABLE_HIP_TRACING=(ON|1)',
  'why': 'Without the ROCm >= 6.2 prefix on CMAKE_PREFIX_PATH find_package(rocprofiler-sdk) fails and HIP tracing '
         'silently compiles out.',
  'fix': 'export ROCM_PATH=<rocm-prefix>; export CMAKE_PREFIX_PATH=$ROCM_PATH:$CMAKE_PREFIX_PATH before the build.'},
 {'id': 'no_nccl_net_guess',
  'kind': 'forbid',
  'pattern': '\\bNCCL_NET=',
  'why': "A NCCL_NET value not exactly matching the plugin's registration name is a hard failure that looks like an "
         'ABI problem.',
  'fix': 'Leave NCCL_NET unset; put the aws-ofi-rccl lib dir on LD_LIBRARY_PATH.'},
 {'id': 'torch_profiler_single_window',
  'kind': 'forbid',
  'pattern': 'schedule\\([^)]*repeat\\s*=\\s*([2-9]|[1-9]\\d+)',
  'why': "A second torch-profiler cycle re-arms roctracer under dftracer's rocprofiler-sdk context and aborts ('_v' "
         'Must be non nullptr).',
  'fix': 'Use repeat=1 and widen active= for more coverage.'},
 {'id': 'torch_profiler_record_shapes',
  'kind': 'require_if',
  'pattern': 'record_shapes\\s*=\\s*True',
  'when': 'on_trace_ready\\s*=\\s*\\S*trace_handler',
  'why': "dftracer's trace_handler derives input_size from event.input_shapes.",
  'fix': 'Pass record_shapes=True to torch.profiler.profile.'},
 {'id': 'rccl_working_env',
  'kind': 'require_if',
  'pattern': 'module\\s+load\\s+\\S*rccl/working-env|FI_MR_CACHE_MONITOR=userfaultfd',
  'when': '(--backend[= ]|backend\\s*=\\s*)[\'\\"]?(nccl|rccl)',
  'flags': 'i',
  'why': 'Multi-node RCCL collectives hang without rccl/working-env (FI_MR_CACHE_MONITOR=userfaultfd).',
  'fix': 'module load rccl/working-env before launching.'},
 {'id': 'rccl_plugin_on_ld_library_path',
  'kind': 'require_if',
  'pattern': 'LD_LIBRARY_PATH=\\S*ofi',
  'when': '(--backend[= ]|backend\\s*=\\s*)[\'\\"]?(nccl|rccl)',
  'flags': 'i',
  'why': 'Without the aws-ofi-rccl plugin on LD_LIBRARY_PATH RCCL silently falls back to host TCP (40%+ slower).',
  'fix': 'export LD_LIBRARY_PATH=<aws-ofi-rccl>/lib:$LD_LIBRARY_PATH.'},
 {'id': 'flux_ddp_exclusive',
  'kind': 'require_if',
  'pattern': 'flux\\s+run\\b[^\\n]*--exclusive',
  'when': 'flux\\s+run\\b[^\\n]*\\b(python3?|torchrun)\\b',
  'why': 'Non-exclusive flux run + DDP can fork-bomb the node (inherited PMI_RANK=0).',
  'fix': 'Launch with flux run --exclusive and unset PMI_*/PALS_*/LDCS_RANKINFO first.'},
 {'id': 'no_hsa_interrupt_off',
  'kind': 'forbid',
  'pattern': 'HSA_ENABLE_INTERRUPT=0',
  'why': 'Busy-wait GPU completion measured +3.78% net worse on a mixed CPU+GPU app (MI300A, 2026-08-05).',
  'fix': 'Drop HSA_ENABLE_INTERRUPT=0 unless the phase is pure-GPU with idle host cores.'},
 {'id': 'no_rocm_smi_perflevel',
  'kind': 'forbid',
  'pattern': 'rocm-smi\\s[^\\n]*--setperflevel',
  'why': 'Admin-gated on LC systems (no sudo); MI300A already boosts under load.',
  'fix': 'Remove it; treat GPU perf level as not tunable.'}]
