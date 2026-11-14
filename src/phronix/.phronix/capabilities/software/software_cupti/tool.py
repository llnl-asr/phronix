"""software_cupti: CUPTI (CUDA Profiling Tools Interface) as dftracer's NVIDIA GPU tracing backend: which CUPTI API dftracer uses (Activity API only: a timeline, not hardware counters), where cupti.h/libcupti.so live in the two CUDA toolkit layouts, building with DFTRACER_ENABLE_CUDA_TRACING (an env var for setup.py, not CMAKE_ARGS) and DFTRACER_CUDA_PATH, the versioned activity-record struct bands per toolkit, clock rebasing onto the dftracer timeline, the CUDA event taxonomy, dropped-record warnings, and the run-time gates (one CUPTI client per process, NVreg_RestrictProfilingToAdminUsers). Load for any DFTRACER_ENABLE_CUDA_TRACING build, any NVIDIA-GPU dftracer session, or on: no CUDA events in the trace / no 'found CUPTI at' configure line, 'CUPTI_ERROR_INSUFFICIENT_PRIVILEGES', 'CUPTI dropped N activity records', 'unknown type CUpti_ActivityKernelN', GPU events at absurd timestamps, nsys/ncu/torch.profiler failing to attach, find reporting no cupti.h."""
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


def _SOFTWARE_CUPTI_judge(commands, rules):
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
    def software_cupti_recipe(section: str = "") -> str:
        """The build/run/env recipe software_cupti knows, as structured JSON: activity_contract, apis, branch_matrix_2026_08_26, buffers, build, clock_rebase, events, findcupti_search_order, layout, preflight_probe, runtime_gates, site_h100_spr, struct_bands.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (activity_contract, apis, branch_matrix_2026_08_26, buffers, build, clock_rebase, events, findcupti_search_order, layout, preflight_probe, runtime_gates, site_h100_spr, struct_bands); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_cupti_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_CUPTI_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_cupti", "sections": sorted(_SOFTWARE_CUPTI_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_CUPTI_RULES]})

    @mcp.tool()
    def software_cupti_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_cupti's rules: cuda_tracing_as_env_not_cmake_args; pin_cuda_path; verify_cupti_header; find_follows_symlinks; no_nsight_bundled_cupti; one_cupti_client.

        Use on a proposed recipe or command list before running it, and after software_cupti_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_CUPTI_judge(commands, _SOFTWARE_CUPTI_RULES))


_SOFTWARE_CUPTI_RECIPE = {'apis': {'activity': {'gives': 'async buffered records of kernels, memcpys, API calls',
                       'overhead': 'low',
                       'used_by_dftracer': True},
          'callback': {'gives': 'sync callbacks at each runtime/driver API entry/exit',
                       'overhead': 'higher',
                       'used_by_dftracer': False},
          'event_metric_legacy': {'gives': 'pre-Volta HW counters',
                                  'overhead': 'high, serializes kernels',
                                  'used_by_dftracer': False},
          'profiling_perfworks': {'gives': 'modern HW counters (ncu)',
                                  'overhead': 'very high, kernel replay',
                                  'used_by_dftracer': False},
          'consequence': 'dftracer CUDA backend = timeline, not counters; GPU counters need ncu/PerfWorks'},
 'activity_contract': ['cuptiActivityRegisterCallbacks(buffer_requested, buffer_completed)',
                       'cuptiActivityEnable(KIND) per kind',
                       'buffer_requested: malloc and hand back',
                       'buffer_completed (CUPTI worker thread): cuptiActivityGetNextRecord, free',
                       'cuptiActivityFlushAll(1) at teardown'],
 'layout': {'cuda_le_10_1': {'header': '<cuda>/extras/CUPTI/include/cupti.h',
                             'lib': '<cuda>/extras/CUPTI/lib64/libcupti.so'},
            'cuda_ge_10_2': {'header': '<cuda>/include/cupti.h', 'lib': '<cuda>/lib64/libcupti.so'},
            'not_cupti': 'nsight-systems/*/target-linux-x64/libcupti.so.* (Nsight injection libs, no headers)',
            'verify': 'ls -L <root>/include/cupti.h  (or find -L ...; plain find does not follow symlinks)'},
 'findcupti_search_order': ['DFTRACER_CUDA_PATH (never silently overridden)',
                            'CUDAToolkit_ROOT / CUDA_TOOLKIT_ROOT_DIR cmake vars',
                            'CUDAToolkit_ROOT / CUDA_HOME / CUDA_PATH env vars (module load cuda sets them)',
                            'find_package(CUDAToolkit)',
                            'nvcc on PATH',
                            '/usr/local/cuda'],
 'build': {'option': 'DFTRACER_ENABLE_CUDA_TRACING (compile-time, default OFF, env var for setup.py, not CMAKE_ARGS)',
           'pip': 'DFTRACER_ENABLE_CUDA_TRACING=ON DFTRACER_CUDA_PATH=<cuda-root> pip install --no-binary dftracer '
                  '<source-or-git-url>',
           'autobuild': './autobuild.sh --with-cuda <cuda-root>  (implies --enable-cuda)',
           'cmake': 'cmake -DDFTRACER_ENABLE_CUDA_TRACING=ON -DDFTRACER_CUDA_PATH=<cuda-root> ..',
           'auto': 'DFTRACER_ENABLE_DYNAMIC_DETECTION=ON enables CUPTI when found',
           'verify_configure': ['-- [DFTRACER] found CUPTI at <root>/include (cuda root <root>)',
                                '-- [DFTRACER] CUDA toolkit version: <x.y.z>'],
           'verify_trace': 'DFTRACER metadata record `build` key has "cuda": 1',
           'branch_check': ["grep -c 'DFTRACER_ENABLE_CUDA_TRACING' CMakeLists.txt",
                            "grep -c 'DFTRACER_ENABLE_PAPI_TRACING\\|DFTRACER_ENABLE_VARIORUM' CMakeLists.txt"]},
 'struct_bands': {'keyed_on': 'DFTRACER_CUDA_VERSION (from CUDAToolkit_VERSION, baked into dftracer_config.hpp), not '
                              'CUPTI_API_VERSION',
                  'columns': ['Kernel',
                              'Memcpy',
                              'MemcpyP2P',
                              'Memset',
                              'Memory',
                              'Sync',
                              'Overhead',
                              'UnifiedMem',
                              'GraphTrace'],
                  '>=13.0': ['Kernel11',
                             'Memcpy6',
                             'PtoP4',
                             'Memset4',
                             'Memory4',
                             'Sync2',
                             'Overhead3',
                             'UM3',
                             'Graph2'],
                  '>=12.9': ['Kernel9',
                             'Memcpy6',
                             'PtoP4',
                             'Memset4',
                             'Memory4',
                             'Sync2',
                             'Overhead3',
                             'UM3',
                             'Graph2'],
                  '>=12.6': ['Kernel9',
                             'Memcpy5',
                             'PtoP4',
                             'Memset4',
                             'Memory4',
                             'Sync',
                             'Overhead3',
                             'UM2',
                             'Graph2'],
                  '>=12.0': ['Kernel9', 'Memcpy5', 'PtoP4', 'Memset4', 'Memory3', 'Sync', 'Overhead', 'UM2', 'Graph'],
                  '>=11.8': ['Kernel8', 'Memcpy5', 'PtoP4', 'Memset4', 'Memory3', 'Sync', 'Overhead', 'UM2', 'Graph'],
                  '>=11.6': ['Kernel7',
                             'Memcpy5',
                             'PtoP4',
                             'Memset4',
                             'Memory3',
                             'Sync',
                             'Overhead',
                             'UM2',
                             'Graph (11.7+ only)'],
                  '>=11.2': ['Kernel6', 'Memcpy4', 'PtoP3', 'Memset3', 'Memory2', 'Sync', 'Overhead', 'UM2', None],
                  '>=11.0': ['Kernel5', 'Memcpy4', 'PtoP3', 'Memset3', None, 'Sync', 'Overhead', 'UM2', None],
                  '10.x': ['Kernel4', 'Memcpy2', None, 'Memset', None, 'Sync', 'Overhead', 'UM2', None],
                  'notes': ['GRAPH_TRACE landed in 11.7 inside the 11.6 band: own #if gate',
                            'absent kinds are #ifdef-gated out of initialize()',
                            'CUDA 12.6 deleted all superseded structs',
                            'new toolkit: add a band, do not widen one',
                            'verified: 10.1, 10.2, 11.1-11.8, 12.2, 12.6, 12.9, 13.1']},
 'clock_rebase': {'factor': 'time_metric_units_per_second(time_metric) / 1e9',
                  'time_diff': 'logger->get_time() - floor(cupti_now * factor)  (sampled once, lazily on first '
                               'record; retried if cuptiGetTimestamp not ready)',
                  'event_ts': 'floor(cupti_ts * factor) + time_diff',
                  'duration': 'transform_time(end, start) floors both endpoints before subtracting',
                  'test': 'test/cuda/check_cuda_trace.py: CUDA events fall inside the issuing app region'},
 'events': {'type': 'CUDA',
            'categories': {'CUDA_RUNTIME_API': 'runtime API calls',
                           'CUDA_DRIVER_API': 'driver API calls',
                           'CUDA_KERNEL': 'kernel launches (kernel symbol)',
                           'CUDA_MEMCPY': 'host/device copies (by direction)',
                           'CUDA_MEMCPY_P2P': 'peer device copies',
                           'CUDA_MEMSET': 'device memsets',
                           'CUDA_MEMORY': 'allocs/frees',
                           'CUDA_SYNC': 'stream/event/context sync',
                           'CUDA_GRAPH': 'graph execution',
                           'CUDA_MARKER': 'NVTX markers',
                           'CUDA_UNIFIED_MEMORY': 'UM faults/migrations/thrashing',
                           'CUDA_OVERHEAD': 'CUPTI overhead'},
            'common_args': ['device_id', 'context_id', 'stream_id', 'correlation_id'],
            'copy_args': ['bytes', 'copy_kind'],
            'kernel_args': ['grid_x', 'block_x', 'registers_per_thread', 'shared memory sizes'],
            'enabled_not_emitted': ['NAME', 'DEVICE', 'CONTEXT', 'EXTERNAL_CORRELATION'],
            'name_truncation_chars': 64,
            'join_key': 'correlation_id'},
 'buffers': {'size': '8 MiB, 8-byte aligned',
             'max_num_records': 0,
             'completion_thread': 'CUPTI worker thread (thread-safe code only)',
             'dropped_warning': 'CUPTI dropped N activity records (WARN, from cuptiActivityGetNumDroppedRecords)',
             'mitigation_order': ['fewer activity kinds', 'shorter run', 'larger buffer'],
             'finalize': 'cuptiActivityFlushAll(1) while logger alive'},
 'runtime_gates': {'one_client_per_process': ['nsys',
                                              'ncu',
                                              'torch.profiler / torch.autograd.profiler with CUDA activity',
                                              'TensorFlow profiler',
                                              'JAX profiler'],
                   'driver_permission': {'param': 'NVreg_RestrictProfilingToAdminUsers',
                                         'ok': 0,
                                         'admin_only': 1,
                                         'error': 'CUPTI_ERROR_INSUFFICIENT_PRIVILEGES',
                                         'check': ['grep -rh RestrictProfiling /etc/modprobe.d/',
                                                   'grep -i RestrictProfiling /proc/driver/nvidia/params']},
                   'runtime_env_needed': 'none beyond dftracer itself'},
 'preflight_probe': {'where': 'compute node',
                     'calls': ['cuptiGetTimestamp(&ts)',
                               'cuptiActivityEnable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL)',
                               'cuptiGetResultString',
                               'cuptiGetVersion(&v)'],
                     'compile': 'gcc probe.c -I$CUDA_ROOT/include -L$CUDA_ROOT/lib64 -lcupti -o probe',
                     'run': 'LD_LIBRARY_PATH=$CUDA_ROOT/lib64:$LD_LIBRARY_PATH ./probe',
                     'success': '0, non-zero ts, CUPTI_SUCCESS',
                     'api_version_map': {'24': 'CUDA 12.6'}},
 'branch_matrix_2026_08_26': {'feature/cupti': {'cupti': True,
                                                'mpi': True,
                                                'papi': False,
                                                'variorum': False,
                                                'service_telemetry': False},
                              'develop': {'cupti': False,
                                          'mpi': True,
                                          'papi': True,
                                          'variorum': True,
                                          'service_telemetry': True}},
 'site_h100_spr': {'date': '2026-08-26',
                   'class': 'matrix-class H100 cluster',
                   'gpus': '4 x H100 80GB HBM3, cc 9.0, driver 610.43.02',
                   'cpus': '2 x Xeon Platinum 8480+ (Sapphire Rapids), 112 cores, 8 NUMA regions, '
                           'RestrictedCoresPerGPU=28',
                   'cuda_without_cupti': '/usr/local/cuda-12.0',
                   'cuda_modules_with_cupti': ['cuda/11.8.0',
                                               'cuda/12.2.2',
                                               'cuda/12.6.0',
                                               'cuda/12.9.1',
                                               'cuda/13.1.1'],
                   'restrict_profiling': 0,
                   'probe_cuda_12_6': 'cuptiGetTimestamp SUCCESS, cuptiActivityEnable SUCCESS, CUPTI_API_VERSION=24',
                   'papi': '5.6.0.0, 17 presets, 19 counters, perf_event PMU spr; rapl disabled; perf_event_uncore '
                           'disabled; no CUDA/NVML component'}}

_SOFTWARE_CUPTI_RULES = [{'id': 'cuda_tracing_as_env_not_cmake_args',
  'kind': 'forbid',
  'pattern': 'CMAKE_ARGS=[^\\n]*DFTRACER_ENABLE_CUDA_TRACING',
  'why': 'setup.py reads DFTRACER_ENABLE_CUDA_TRACING from the environment; inside CMAKE_ARGS it never reaches cmake '
         'and the build has no CUPTI.',
  'fix': 'Set DFTRACER_ENABLE_CUDA_TRACING=ON (and DFTRACER_CUDA_PATH) as environment variables for pip.'},
 {'id': 'pin_cuda_path',
  'kind': 'require_if',
  'pattern': 'DFTRACER_CUDA_PATH=\\S+|--with-cuda\\s+\\S+',
  'when': 'DFTRACER_ENABLE_CUDA_TRACING=ON',
  'why': 'Without a pinned path FindCUPTI may pick a toolkit without cupti.h (e.g. a stripped /usr/local/cuda) and '
         'silently build CUDA tracing off.',
  'fix': 'Add DFTRACER_CUDA_PATH=<module-managed cuda root that has include/cupti.h>.'},
 {'id': 'verify_cupti_header',
  'kind': 'require_if',
  'pattern': 'ls\\s+-L\\s+\\S*cupti\\.h|find\\s+-L\\s[^\\n]*cupti',
  'when': 'DFTRACER_ENABLE_CUDA_TRACING=ON|--with-cuda',
  'why': 'A CUDA toolkit can exist without CUPTI; confirm cupti.h (following symlinks) before building.',
  'fix': 'Run `ls -L <cuda-root>/include/cupti.h` before the build.'},
 {'id': 'find_follows_symlinks',
  'kind': 'forbid',
  'pattern': '\\bfind\\s+(?!-L)[^|;\\n]*cupti',
  'why': 'Site CUDA trees are symlinks; plain find does not follow them and falsely reports no cupti.h.',
  'fix': 'Use find -L, or ls -L <root>/include/cupti.h.'},
 {'id': 'no_nsight_bundled_cupti',
  'kind': 'forbid',
  'pattern': '(DFTRACER_CUDA_PATH|CUDA_HOME|CUDA_PATH|CUDAToolkit_ROOT)=\\S*nsight|-L\\S*nsight-systems',
  'why': 'libcupti.so.* under nsight-systems/*/target-linux-x64 are Nsight injection libraries with no headers or '
         'SDK; they cannot be built against.',
  'fix': 'Point DFTRACER_CUDA_PATH at a real CUDA toolkit root with include/cupti.h.'},
 {'id': 'one_cupti_client',
  'kind': 'forbid_if',
  'pattern': '(^|[\\s;&|])(nsys|ncu)\\s',
  'when': 'DFTRACER_ENABLE=1|DFTRACER_INIT=',
  'why': 'CUPTI allows one profiling client per process; dftracer CUDA tracing and nsys/ncu in the same run means '
         'one fails to attach.',
  'fix': 'Run nsys/ncu in a separate run without dftracer enabled.'}]
