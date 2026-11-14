"""software_megatron_deepspeed: Megatron-DeepSpeed (BERT-Base, GPT) under dftracer on Tuolumne MI300A (4 nodes x 4 GPUs = 16 ranks): the RCCL transport fix (put the site aws-ofi-rccl plugin on LD_LIBRARY_PATH, leave NCCL_NET unset - NCCL_NET=libfabric hard-fails because the plugin registers as 'AWS Libfabric'), --num-workers 2 for BERT MLM masking, train_step (not wall time) as the metric, and the confirmed negative/null results (bf16, ZeRO-1, flash-attn flags, hipBLASLt, NUMA, rocm leakfix). Load for any Megatron-DeepSpeed session, or when RCCL silently falls back to TCP sockets, NCCL_NET=libfabric fails with what looks like a plugin ABI error, train_step is CPU-bound at --num-workers 0, or session_final_report drops config.ini entries."""
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


def _SOFTWARE_MEGATRON_DEEPSPEED_judge(commands, rules):
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
    def software_megatron_deepspeed_recipe(section: str = "") -> str:
        """The build/run/env recipe software_megatron_deepspeed knows, as structured JSON: env, final_report, flags, gaps, measurement, results, system.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (env, final_report, flags, gaps, measurement, results, system); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_megatron_deepspeed_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_MEGATRON_DEEPSPEED_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_megatron_deepspeed", "sections": sorted(_SOFTWARE_MEGATRON_DEEPSPEED_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_MEGATRON_DEEPSPEED_RULES]})

    @mcp.tool()
    def software_megatron_deepspeed_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_megatron_deepspeed's rules: no_nccl_net_set; aws_ofi_rccl_on_ld_path; bert_num_workers_nonzero; no_flash_attn_flags; no_zero_stage_1_bert; no_bf16_mi300a.

        Use on a proposed recipe or command list before running it, and after software_megatron_deepspeed_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_MEGATRON_DEEPSPEED_judge(commands, _SOFTWARE_MEGATRON_DEEPSPEED_RULES))


_SOFTWARE_MEGATRON_DEEPSPEED_RECIPE = {'system': {'machine': 'Tuolumne (AMD MI300A APU)',
            'shape': '4 nodes x 4 GPUs = 16 ranks',
            'model': 'BERT-Base (GPT-350M sibling)',
            'iterations': 400},
 'env': {'LD_LIBRARY_PATH': '<aws-ofi-rccl prefix>/lib:$LD_LIBRARY_PATH',
         'NCCL_NET': "UNSET (never 'libfabric')",
         'plugin_registration_name': 'AWS Libfabric',
         'verify': 'NCCL_DEBUG=INFO shows the libfabric net plugin, not Socket'},
 'flags': {'good': ['--num-workers 2'],
           'inert_or_bad': {'--bf16': '-25% (GPT-350M sibling session)',
                            'ZeRO stage 1': '-20%/+20% regression, both transports',
                            '--use-flash-attn*': 'silent no-op (FlashAttention absent)',
                            'TORCH_BLAS_PREFER_HIPBLASLT': 'inert',
                            'kernel fusion': 'already on by default',
                            'NUMA/affinity': 'no-op on MI300A APU'}},
 'measurement': {'metric': 'train_step summed over 400 iterations',
                 'not': 'wall time (40-48 s startup variance)',
                 'noise_band': {'socket_transport_n3': '4.9%', 'libfabric_n4': '1.9%'},
                 'share_denominator': 'per-rank wall (~198 s), not rank-summed App total',
                 'replicates': '>= 3, second replicate for single-run probes'},
 'results': {'rccl_transport_fix': '-43.1%',
             'num_workers_2': '-8.2%',
             'total': '47.8% train_step speedup',
             'rocm_6_4_3leakfix': 'memory-leak fix only; perf claim unsupported (-2.2%, overlapping)'},
 'final_report': {'copy_missed_scripts': ['env.sh',
                                          'env_ofi.sh',
                                          'env_baserocm.sh',
                                          'ab_driver*.sh',
                                          'lever_driver.sh',
                                          'run_ab_*.sh',
                                          'run_ofi_*.sh',
                                          'run_L_*.sh',
                                          'ds_config_bert_*.json',
                                          'ab_summarize.py'],
                  'anonymize': {'alloc id': '${1:?...}', 'dataset path': '${DATASET_ROOT} from config.ini'},
                  'config_ini': 'regenerated each call; re-append manual vars',
                  'overwrite_semantics': {'overwrite=False + blank': 'keep',
                                          'overwrite=False + text': 'write',
                                          'overwrite=True': 'write'}},
 'gaps': ['FlashAttention (ROCm/CK build)',
          'checkpoint I/O',
          'HBM roofline (no counter)',
          'pipeline_plan.md missing',
          '2nd replicate: --log-interval 10, ZeRO-1 on libfabric']}

_SOFTWARE_MEGATRON_DEEPSPEED_RULES = [{'id': 'no_nccl_net_set',
  'kind': 'forbid',
  'pattern': '\\bNCCL_NET=',
  'why': "The aws-ofi-rccl plugin registers as 'AWS Libfabric'; NCCL_NET=libfabric (any value) mismatches and "
         'hard-fails, easily misread as an ABI error.',
  'fix': "Remove the NCCL_NET assignment (unset NCCL_NET); just put the plugin's lib dir on LD_LIBRARY_PATH."},
 {'id': 'aws_ofi_rccl_on_ld_path',
  'kind': 'require_if',
  'pattern': 'LD_LIBRARY_PATH=[^\\n]*aws-ofi-rccl',
  'when': 'pretrain_(bert|gpt)\\.py|megatron|deepspeed',
  'flags': 'i',
  'why': 'Without the aws-ofi-rccl plugin on LD_LIBRARY_PATH RCCL silently falls back to host TCP sockets (43% '
         'slower).',
  'fix': 'export LD_LIBRARY_PATH=<aws-ofi-rccl prefix>/lib:$LD_LIBRARY_PATH before launching.'},
 {'id': 'bert_num_workers_nonzero',
  'kind': 'forbid_if',
  'pattern': '--num-workers[ =]0\\b',
  'when': 'pretrain_bert\\.py',
  'why': "BERT's inline MLM masking is per-batch CPU work on the critical path at --num-workers 0.",
  'fix': 'Use --num-workers 2.'},
 {'id': 'no_flash_attn_flags',
  'kind': 'forbid',
  'pattern': '--use-flash-attn',
  'why': 'All --use-flash-attn* flags are silent no-ops: FlashAttention is not installed (needs a multi-hour ROCm/CK '
         'build).',
  'fix': 'Drop the flag, or build FlashAttention for ROCm first and verify it is exercised.'},
 {'id': 'no_zero_stage_1_bert',
  'kind': 'forbid_if',
  'pattern': '--zero-stage[ =]1\\b',
  'when': 'pretrain_bert\\.py',
  'why': 'ZeRO-1 regressed -20%/+20% on both transports; optimizer-state savings are 1.4% of HBM at BERT-Base size.',
  'fix': 'Leave ZeRO disabled (stage 0) for BERT-Base.'},
 {'id': 'no_bf16_mi300a',
  'kind': 'forbid_if',
  'pattern': '--bf16\\b',
  'when': 'pretrain_(bert|gpt)\\.py',
  'why': 'bf16 measured -25% on this system (GPT-350M sibling session).',
  'fix': 'Use the default precision (fp16/fp32 as configured) unless a new replicate-confirmed A/B shows otherwise.'}]
