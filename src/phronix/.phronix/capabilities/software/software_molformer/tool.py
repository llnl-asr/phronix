"""software_molformer: IBM MoLFormer (chemical-language transformer; PyTorch + PyTorch Lightning + apex, plus a Ray Train/Tune variant) build/annotate/run facts on ROCm (Tuolumne MI300A): ROCm-matched torch wheel, ROCm/apex fork, dftracer HIP-tracing build, entry-point-only initialize_log, --exclusive flux launch and PMI-var unset against the DDP fork bomb, 1-task-per-node multi-node launch, HF revision pin and cache on PFS, torch-profiler windows. Load for any MoLFormer work, or on: empty/near-empty dftracer trace with no error; hundreds of `bash wrapper.sh` processes / no output for minutes; 'You requested gpu: [0,1,2,3] But your machine only has: [0]'; 'Duplicate GPU detected : rank N and rank 0 both on CUDA device' (ncclInvalidUsage); KeyError 'LSB_MCPU_HOSTS' / 'NCCL_IB_CUDA_SUPPORT'; 'Child process ... terminated with code -6' / exit 137; libcaffe2_nvrtc.so not found; nvcc / CUDA_HOME missing building apex; lightning_fabric Ampere-capability crash; Ray driver idle with 'cluster only has ... GPUs available'; LocalEntryNotFoundError for ibm/MoLFormer-XL-both-10pct; `agent.cpp:640] Check failed: '_v' Must be non nullptr`; zero PP events."""
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


def _SOFTWARE_MOLFORMER_judge(commands, rules):
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
    def software_molformer_recipe(section: str = "") -> str:
        """The build/run/env recipe software_molformer knows, as structured JSON: annotation, apex, bringup_cost, dftracer_build, env, failure_triage, launch_multi_node, launch_single_node, lightning_patches, platform, ray_variant, recover_fork_bomb, torch_profiler, trace_verification, tuning_measured.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (annotation, apex, bringup_cost, dftracer_build, env, failure_triage, launch_multi_node, launch_single_node, lightning_patches, platform, ray_variant, recover_fork_bomb, torch_profiler, trace_verification, tuning_measured); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_molformer_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_MOLFORMER_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_molformer", "sections": sorted(_SOFTWARE_MOLFORMER_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_MOLFORMER_RULES]})

    @mcp.tool()
    def software_molformer_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_molformer's rules: ddp_flux_exclusive; ddp_unset_pmi; multinode_one_task_per_node; apex_rocm_fork; no_expandable_segments; profiler_no_repeat_ge2; hf_download_pinned_revision; ray_address_exported; ray_dataset_csv_path; ray_join_success_string.

        Use on a proposed recipe or command list before running it, and after software_molformer_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_MOLFORMER_judge(commands, _SOFTWARE_MOLFORMER_RULES))


_SOFTWARE_MOLFORMER_RECIPE = {'platform': {'system': 'Tuolumne (AMD MI300A APU, 4 GPUs/node)',
              'rocm_module': 'rocm/6.3.1',
              'torch_wheel': 'ROCm 6.3-series build matching the module (not 6.1 / 6.4)',
              'python': '3.13 venv',
              'upstream': 'https://github.com/IBM/molformer'},
 'env': {'LD_LIBRARY_PATH_prepend': '<venv>/lib/python3.13/site-packages/torch/lib (libcaffe2_nvrtc.so)',
         'unset_before_python': ['PMI_RANK',
                                 'PMI_SIZE',
                                 'PMI_FD',
                                 'PALS_APID',
                                 'PALS_APINFO',
                                 'PALS_NODEID',
                                 'PALS_RANKID',
                                 'PALS_SPOOL_DIR',
                                 'LDCS_RANKINFO'],
         'unsupported': {'PYTORCH_HIP_ALLOC_CONF': 'expandable_segments:True is a no-op with warning on this ROCm'},
         'watchdog_off_does_not_fix_abort': ['TORCH_NCCL_ASYNC_ERROR_HANDLING=0', 'TORCH_NCCL_ENABLE_MONITORING=0']},
 'apex': {'repo': 'https://github.com/ROCm/apex',
          'never': 'https://github.com/NVIDIA/apex (--cuda_ext needs nvcc/CUDA_HOME)',
          'toolchain': 'session HIP toolchain'},
 'lightning_patches': ['skip lightning_fabric Ampere-capability probe on ROCm',
                       'multi-node branch: use pre-set MASTER_ADDR/NODE_RANK instead of LSB_MCPU_HOSTS (LSF)',
                       "os.environ.get('NCCL_IB_CUDA_SUPPORT') instead of subscript"],
 'dftracer_build': {'dftracer': 'pip install git+<dftracer repo>@develop',
                    'env': {'DFTRACER_ENABLE_HIP_TRACING': 'ON',
                            'CC': '$(which mpicc)',
                            'CXX': '$(which mpicxx)',
                            'CMAKE_PREFIX_PATH': '$ROCM_PATH'},
                    'pydftracer': '@develop (PyPI lacks dftracer.python.torch / trace_handler)',
                    'rocprofiler_sdk': 'already in site ROCm trees (cmake config, headers, librocprofiler-sdk.so)',
                    'known_pitfalls': ['bug-dftracer-stale-brahma-after-pip-uninstall',
                                       'bug-dftracer-crayclang-rpath-shadows-libstdcxx']},
 'annotation': {'entry_points': ['train_pubchem_light.py', 'finetune_pubchem_light*.py (3 files)'],
                'imported_no_init': ['pubchem_encoder.py', 'dataset_pubchem.py'],
                'rule': 'initialize_log()/finalize() exactly once in the `if __name__ == "__main__"` entry; @dft_fn '
                        'elsewhere'},
 'launch_single_node': {'command': 'flux run -N 1 -n 1 --exclusive <wrapper.sh> python train_pubchem_light.py --gpus '
                                   '4 ...',
                        'why_exclusive': 'non-exclusive gives a fair-share slice (1 of 4 GPUs) -> '
                                         'MisconfigurationException -> PMI-env fork bomb'},
 'launch_multi_node': {'command': 'flux run -N4 -n4 -c 96 -g 4 <wrapper.sh> python train_pubchem_light.py '
                                  '--num_nodes 4 --gpus 4 ...',
                       'tasks': 'one flux task per node; Lightning spawns the 4 local ranks',
                       'env': ['MASTER_ADDR', 'NODE_RANK'],
                       'gate': 'standalone cross-node all-reduce, 4 ranks 1/node, before the workload'},
 'recover_fork_bomb': ['flux proxy <alloc> flux cancel <jobid>',
                       'flux proxy <alloc> flux run -N1 -n1 --requires=hosts:<node> ps aux | grep -c <script_name>'],
 'tuning_measured': {'setup': '1 node x 4 MI300A, ~1M-param validation config, 20K-molecule PubChem slice, DDP world '
                              '4, 1 epoch / 157 steps',
                     'baseline_b32_w2': '536 samples/s',
                     'bf16_mixed': '307 (-43%, rejected)',
                     'workers_1': '525 (~neutral)',
                     'batch_64': '970 (+81%)',
                     'batch_128_w2': '1638 (+206%, best)',
                     'retest_bf16_at': '~350M-param production config'},
 'torch_profiler': {'reliable': 'one rank, short window (wait=2, warmup=1, active=2)',
                    'long_window_4rank': 'wait=5,warmup=2,active=10 -> SIGABRT (open issue)',
                    'full_coverage': 'schedule(wait=0, warmup=0, active=1_000_000, repeat=1)',
                    'forbidden': 'repeat>=2 (rocprofiler second-cycle crash)',
                    'untested': 'wait=0,warmup=0,active=K,repeat=0',
                    'verify': 'count cat="PP" events directly in every compacted chunk (PP ~0.03% of events)'},
 'trace_verification': {'categories': ['HIP_RUNTIME_API',
                                       'KERNEL_DISPATCH',
                                       'MEMORY_COPY',
                                       'SCRATCH_MEMORY',
                                       'PAGE_MIGRATION',
                                       'RCCL_API',
                                       'PP',
                                       'POSIX',
                                       'STDIO'],
                        'cheapest_check': 'trace metadata `used` map {LIBC_IO, HIP, PYTHON, torch_profiler, '
                                          'python_function}',
                        'service_counters': 'non-empty traces/dftracer_service/<hostname>/ file'},
 'failure_triage': {'chain': 'silent SIGABRT of one local rank (code -6) -> Lightning SIGKILLs siblings (137) -> '
                             'ncclRemoteError on peers -> flux exit-timeout kill',
                    'oom_check': 'memory.events oom/oom_kill from INSIDE the job cgroup (login-side probe reads the '
                                 'wrong cgroup)',
                    'status': 'open; reproduces at step ~19-36/40, HIP-only run too'},
 'ray_variant': {'script': 'molformer_ray_descriptors.py',
                 'env': {'RAY_ADDRESS': '<head_ip>:<port>',
                         'DATASET_CSV_PATH': '/p/lustre5/$USER/ray_molformer/<run_name>/pubchem_filtered.csv '
                                             '(literal Lustre path, reuse shared CSV)',
                         'HF_HOME': '/p/lustre5/$USER/ray_molformer/hf_cache (PFS, never $HOME)',
                         'HF_HUB_OFFLINE': '1',
                         'TRANSFORMERS_OFFLINE': '1'},
                 'export_HF_HOME_at': ['head ray start --head',
                                       'head python launch',
                                       'each worker ray start --address='],
                 'hf_revision': '7b12d946c181a37f6012b9dc3b002275de070314',
                 'hf_download': 'hf download ibm/MoLFormer-XL-both-10pct --revision '
                                '7b12d946c181a37f6012b9dc3b002275de070314 --cache-dir $HF_HOME/hub',
                 'prewarm': 'single-process AutoConfig.from_pretrained(<repo>, revision=<pin>, '
                            'trust_remote_code=True) before the multi-actor run',
                 'topology': '4 nodes, head also a worker: ray start --head --num-gpus=4; '
                             'ScalingConfig(num_workers=16)',
                 'join_success_string': 'Ray runtime started.',
                 'worker_lifetime': 'poll a completion-marker file the head touches on exit',
                 'dataset_dir': '<WS>/dataset/<run_name> must be a symlink to Lustre',
                 'default_worker_patch': 'ray/_private/workers/default_worker.py: try: import torch (swallow '
                                         'ImportError) before dftracer initialize_log()'},
 'bringup_cost': {'bucket': '1864.4s molformer_ray_descriptors category',
                  'real_cause': 'hipModuleLoad x252 @ ~234ms (58.9s of 75-81s first forward)',
                  'not': 'HF model load (7.4s/worker)',
                  'torch_bundles_rocm': '~9.7GB ROCm libs in <venv>/torch/lib, /opt/rocm ignored',
                  'prewarm_result': 'null (opt5 +1.1%, noise 6.3%)'}}

_SOFTWARE_MOLFORMER_RULES = [{'id': 'ddp_flux_exclusive',
  'kind': 'forbid',
  'pattern': '^(?=.*flux\\s+(run|submit)\\b)(?=.*(train_pubchem_light|finetune_pubchem_light))(?!.*--exclusive)(?!.*\\s-g\\s*\\d)',
  'why': "A non-exclusive single-task flux run gets 1 of 4 GPUs; Lightning's MisconfigurationException plus "
         'inherited PMI_RANK=0 then fork-bombs the node.',
  'fix': 'Add --exclusive to the flux run/submit (single node) or request GPUs per node with -g 4 (one task per '
         'node).'},
 {'id': 'ddp_unset_pmi',
  'kind': 'require_if',
  'pattern': 'unset\\s+[^\\n]*PMI_RANK',
  'when': 'flux\\s+(run|submit)\\b[^\\n]*(train_pubchem_light|finetune_pubchem_light)',
  'why': 'Flux sets PMI_RANK=0/PMI_SIZE=1/PALS_* for every run; Lightning DDP children inherit them and relaunch '
         'forever.',
  'fix': 'unset PMI_RANK PMI_SIZE PMI_FD PALS_APID PALS_APINFO PALS_NODEID PALS_RANKID PALS_SPOOL_DIR LDCS_RANKINFO '
         'before python.'},
 {'id': 'multinode_one_task_per_node',
  'kind': 'forbid_if',
  'pattern': 'flux\\s+(run|submit)\\b[^\\n]*\\s-g\\s*1\\b',
  'when': '--num_nodes\\s+([2-9]|\\d{2,})',
  'why': "One flux task per GPU hands every task the same device: 'Duplicate GPU detected ... ncclInvalidUsage'.",
  'fix': 'One task per node: flux run -N<n> -n<n> -c 96 -g 4 ... --num_nodes <n> --gpus 4.'},
 {'id': 'apex_rocm_fork',
  'kind': 'forbid',
  'pattern': 'github\\.com[/:]NVIDIA/apex',
  'flags': 'i',
  'why': 'Upstream NVIDIA/apex --cuda_ext hard-requires nvcc/CUDA_HOME, absent on ROCm.',
  'fix': 'Build https://github.com/ROCm/apex against the HIP toolchain.'},
 {'id': 'no_expandable_segments',
  'kind': 'forbid',
  'pattern': 'PYTORCH_HIP_ALLOC_CONF=\\S*expandable_segments',
  'why': 'expandable_segments is not supported on this ROCm platform (warning, silent no-op) and misattributes '
         'speedups.',
  'fix': 'Drop the variable; tune batch size instead.'},
 {'id': 'profiler_no_repeat_ge2',
  'kind': 'forbid',
  'pattern': 'schedule\\([^\\n]*repeat\\s*=\\s*([2-9]|\\d{2,})',
  'why': 'A second torch-profiler cycle crashes the process under rocprofiler-sdk HIP tracing.',
  'fix': 'Use repeat=1 with wait=0, warmup=0, active=<very large> for full coverage, or a short single window on one '
         'rank.'},
 {'id': 'hf_download_pinned_revision',
  'kind': 'forbid',
  'pattern': '^(?!.*--revision).*hf\\s+download\\s+ibm/MoLFormer',
  'why': 'The app pins revision 7b12d946c181a37f6012b9dc3b002275de070314; a main-only cache makes every actor fail '
         'with LocalEntryNotFoundError.',
  'fix': 'hf download ibm/MoLFormer-XL-both-10pct --revision 7b12d946c181a37f6012b9dc3b002275de070314 --cache-dir '
         '$HF_HOME/hub'},
 {'id': 'ray_address_exported',
  'kind': 'require_if',
  'pattern': 'RAY_ADDRESS=\\S+',
  'when': 'molformer_ray_descriptors\\.py',
  'why': 'ray.init() without RAY_ADDRESS silently builds an isolated single-node cluster and the driver idles '
         'forever.',
  'fix': 'export RAY_ADDRESS=<head_ip>:<port> before the training script.'},
 {'id': 'ray_dataset_csv_path',
  'kind': 'require_if',
  'pattern': 'DATASET_CSV_PATH=\\S+',
  'when': 'molformer_ray_descriptors\\.py',
  'why': 'The script-relative fallback path does not exist under annotated/src/../dataset.',
  'fix': 'export DATASET_CSV_PATH=<literal Lustre path of the shared CSV>.'},
 {'id': 'ray_join_success_string',
  'kind': 'forbid',
  'pattern': 'Successfully started Ray runtime',
  'why': "Ray's CLI never prints that string (it prints 'Ray runtime started.'), so the retry loop treats every join "
         'as failed.',
  'fix': "grep for 'Ray runtime started.'"}]
