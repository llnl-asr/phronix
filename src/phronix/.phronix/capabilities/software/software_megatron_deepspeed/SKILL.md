---
name: software_megatron_deepspeed
description: Megatron-DeepSpeed (BERT-Base, GPT) under dftracer on Tuolumne MI300A (4 nodes x 4 GPUs = 16 ranks): the RCCL transport fix (put the site aws-ofi-rccl plugin on LD_LIBRARY_PATH, leave NCCL_NET unset - NCCL_NET=libfabric hard-fails because the plugin registers as 'AWS Libfabric'), --num-workers 2 for BERT MLM masking, train_step (not wall time) as the metric, and the confirmed negative/null results (bf16, ZeRO-1, flash-attn flags, hipBLASLt, NUMA, rocm leakfix). Load for any Megatron-DeepSpeed session, or when RCCL silently falls back to TCP sockets, NCCL_NET=libfabric fails with what looks like a plugin ABI error, train_step is CPU-bound at --num-workers 0, or session_final_report drops config.ini entries.
---
Cross-references: [[software_rocm]] [[software_mpi]] [[dftracer_opt_kb]] [[dftracer_optimize]] [[dftracer_report]] [[system_tuolumne]] [[software_flux]] [[capability_builder]]

# software_megatron_deepspeed

Converted from dftracer-agents skill `software-megatron-deepspeed`. Tools: `software_megatron_deepspeed_recipe` (predictor) and `software_megatron_deepspeed_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Put the site `aws-ofi-rccl` plugin's lib dir on LD_LIBRARY_PATH; otherwise RCCL silently falls back to host TCP sockets (-43.1% train_step when fixed).
- Leave `NCCL_NET` UNSET. Do NOT set `NCCL_NET=libfabric`: the plugin registers as `AWS Libfabric`, the name mismatch forces a hard failure that looks like an ABI incompatibility but is a naming mismatch.
- Use `--num-workers 2` for BERT: inline MLM masking (`create_masked_lm_predictions`) is per-batch CPU work on the critical path at `--num-workers 0` (-8.2%).
- Metric of record is `train_step` summed over the iterations (400), not wall time: wall time carries ~40-48 s of allocation/init startup variance. Noise band ~4.9% (socket transport, n=3), ~1.9% (libfabric-fixed, n=4).
- Compute percentages against per-rank wall time (~198 s), never dfanalyzer's rank-summed App total (1933.3 s) - that understates shares ~16x.
- Before treating a transport comparison (gloo vs nccl) as evidence, confirm which transport each run actually used.
- Void a baseline contaminated by a transient filesystem stall (e.g. 140 s of `stat`); re-measure, do not optimize against it.
- Do not re-test the recorded negative/null results from scratch: bf16 -25% (GPT-350M sibling session), ZeRO-1 -20%/+20% regression on BOTH transports (optimizer-state savings only 1.4% of HBM), TORCH_BLAS_PREFER_HIPBLASLT inert, all four --use-flash-attn* flags silently no-op (FlashAttention not installed), kernel fusion already on by default, NUMA/affinity no-op on MI300A APU.
- `rocm/6.4.3leakfix` is kept for its memory-leak fix only; its -4.9% is NOT a supported performance claim (clean A/B -2.2%, overlapping ranges).
- final_report: copy every driver/env script the glob misses (env*.sh, ab_driver*.sh, lever_driver.sh, run_ab_*/run_ofi_*/run_L_*.sh, ds_config_bert_*.json, ab_summarize.py) into final_report/scripts/ and anonymize (alloc id -> `${1:?...}`, dataset path -> `${DATASET_ROOT}` from config.ini).
- Re-calling `session_final_report` regenerates config.ini from scratch: re-append manual vars (e.g. DATASET_ROOT) after every call, before the final privacy scan.
- `session_final_report` report_md/conversation_md/readme_md: overwrite=False + blank string keeps existing content; overwrite=False + non-blank OR overwrite=True writes what you pass. There is no 'keep existing' placeholder ("KEEP" is written literally). Resupply full content in the same call.
- Write `pipeline_plan.md` and dispatch stages through it (it was skipped in the recorded session - a process gap).

## Constraints
- Findings are from Tuolumne MI300A, BERT-Base, 4 nodes / 16 ranks, 400 iterations; re-verify on other systems/models.
- Megatron-DeepSpeed is software (annotated/instrumented by dftracer), not a workload, per the software-vs-workload naming convention.
- Honest gaps: FlashAttention untested (multi-hour ROCm/CK build; highest remaining ceiling), checkpoint I/O never exercised, memory-bandwidth roofline unresolved (no HBM counter), two single-replicate probes (--log-interval 10, ZeRO-1 on libfabric) need a second replicate.
- Dangling references not recovered: software-megatron-deepspeed-compute-tuning-findings and project-megatron-deepspeed-gpt-pipeline; do not fabricate them.
- privacy_scan operates project-wide, not only over the session workspace.

## Corner cases
### RCCL silently using host TCP sockets (slow allreduce, no error)
Cause: aws-ofi-rccl plugin dir not on LD_LIBRARY_PATH. Fix: prepend its lib dir, leave NCCL_NET unset. Verify: NCCL_DEBUG=INFO shows the AWS Libfabric net plugin; train_step -43%.

### Hard failure with NCCL_NET=libfabric, misread as 'plugin is ABI-incompatible'
Cause: plugin registers as 'AWS Libfabric'; the name never matches 'libfabric'. Fix: unset NCCL_NET.

### gloo vs nccl differ by only +1.2%
Cause: both were on host TCP at the time - null by construction. Fix: fix the transport first, then compare.

### BERT appears to have 9x GPT's I/O (7.3% POSIX @ 17.7 MB/s)
Cause: transient Lustre stall (140.42 s of stat); standalone re-measure 0.19 ms. Fix: void the baseline.

### --use-flash-attn* flags change nothing
Cause: FlashAttention dependency absent; flags silently no-op. Fix: build FlashAttention for ROCm/CK first (untested, multi-hour).

### Manually appended config.ini vars (DATASET_ROOT) vanish
Cause: session_final_report regenerates config.ini on each call. Fix: re-append after every call, then privacy scan.

### README/report replaced by the literal text 'KEEP'
Cause: non-blank text with overwrite=False is written. Fix: pass blank to keep, or the full content.

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `software_megatron_deepspeed_recipe` renders the recipe; validator `software_megatron_deepspeed_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_nccl_net_set` fails: Remove the NCCL_NET assignment (unset NCCL_NET); just put the plugin's lib dir on LD_LIBRARY_PATH. Then render with `software_megatron_deepspeed_recipe` and validate again.
- `aws_ofi_rccl_on_ld_path` fails: export LD_LIBRARY_PATH=<aws-ofi-rccl prefix>/lib:$LD_LIBRARY_PATH before launching. Then render with `software_megatron_deepspeed_recipe` and validate again.
- `bert_num_workers_nonzero` fails: Use --num-workers 2. Then render with `software_megatron_deepspeed_recipe` and validate again.
- `no_flash_attn_flags` fails: Drop the flag, or build FlashAttention for ROCm first and verify it is exercised. Then render with `software_megatron_deepspeed_recipe` and validate again.
- `no_zero_stage_1_bert` fails: Leave ZeRO disabled (stage 0) for BERT-Base. Then render with `software_megatron_deepspeed_recipe` and validate again.
- `no_bf16_mi300a` fails: Use the default precision (fp16/fp32 as configured) unless a new replicate-confirmed A/B shows otherwise. Then render with `software_megatron_deepspeed_recipe` and validate again.

## Self-heal
- If train_step does not improve after the transport fix, check LD_LIBRARY_PATH inside the launched ranks (flux/srun environment) and NCCL_DEBUG=INFO output for the selected net plugin.

## Self-learn
- Record each new lever as a replicate-confirmed A/B (n>=3) with its noise band; add negative results so later sessions skip them; fold in the GPT-350M and compute-tuning write-ups if found.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this software goes into software_megatron_deepspeed via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (undated, Tuolumne MI300A, 16 ranks, 400 iters) aws-ofi-rccl lib dir on LD_LIBRARY_PATH with NCCL_NET unset (-43.1%) + --num-workers 2 (-8.2%) = 47.8% train_step speedup, replicate-confirmed.

## Source: dftracer-agents `software-megatron-deepspeed` (verbatim, headings demoted)
_Original description:_ > Megatron-DeepSpeed BERT-Base dftracer pipeline findings on Tuolumne (AMD MI300A, 4 nodes / 16 ranks) — RCCL transport fix, dataloader worker fix, corrected measurement methodology, and confirmed negative/null results. Megatron-DeepSpeed is annotated/instrumented by dftracer (software-* naming, not workload-*, per the software-vs-workload naming convention). Load this skill for any Megatron-DeepSpeed session.

Cross-references: [[software-rocm]] [[software-mpi]] [[dftracer-optimization-kb]] [[system-tuolumne]]

---

#### Session: BERT-Base, 4 nodes x 4 GPUs = 16 ranks, MI300A

Full pipeline complete: annotation (11 files / 231 dftracer decorators),
multi-replicate A/B baselines, root-cause diagnosis, 4-dimension optimization sweep
(I/O, communication, compute, memory all walked), final_report assembled and
privacy-clean.

**Headline: measured 47.8% train_step speedup** (400 iterations, 16 ranks / 4 nodes),
replicate-confirmed, from two config-only changes:

1. **RCCL transport fix (-43.1%).** RCCL was silently falling back to host TCP
   sockets because the site's `aws-ofi-rccl` plugin was never on
   `LD_LIBRARY_PATH`. Fix: add the plugin's lib dir to `LD_LIBRARY_PATH`, and
   leave `NCCL_NET` UNSET — do NOT set `NCCL_NET=libfabric`, since the plugin
   registers as `AWS Libfabric` and the name mismatch forces a hard failure that
   is easy to misread as an ABI incompatibility rather than a naming mismatch.
   See `software-rocm`'s "RCCL transport selection" section for the generic
   version of this lesson.
2. **`--num-workers 2` (-8.2%).** BERT's inline MLM masking
   (`create_masked_lm_predictions`) is real per-batch CPU work sitting on the
   critical path at `--num-workers 0`.

`train_step` summed over 400 iterations is the metric of record — wall time is
NOT, since it is dominated by ~40-48s of allocation/init-time startup variance
that swamps the per-step signal. Noise band: ~4.9% on the socket-transport
config (n=3 replicates), ~1.9% on the libfabric-fixed config (n=4 replicates).

#### Corrected findings (each cost real time to root-cause — read before re-deriving)

- **"Plugin is ABI-incompatible" — WRONG.** It's a naming mismatch
  (`NCCL_NET=libfabric` never matches the plugin's `AWS Libfabric` registration
  name), not an ABI issue.
- **"gloo vs nccl gave only +1.2%, so transport doesn't matter" — SUPERSEDED.**
  Both backends were actually on host TCP at the time of that comparison; the
  comparison was null by construction, not evidence that transport is
  irrelevant.
- **"BERT has 9x GPT's I/O (7.3% POSIX @ 17.7 MB/s)" — RETRACTED.** One-off
  transient Lustre stall (140.42s of `stat` calls); re-measured standalone at
  0.19ms. The contaminated baseline was voided, not optimized against.
- Percentages were originally computed against dfanalyzer's rank-summed App
  total (1933.3s), not per-rank wall time (~198s) — this understated shares by
  ~16x. All figures in this skill are corrected.
- `rocm/6.4.3leakfix` "-4.9%" is **NOT SUPPORTED as a performance claim** (a
  clean A/B gave -2.2% with overlapping ranges) — keep it for its real
  memory-leak fix, not for a performance win.

#### Negative/null results (recorded so future sessions don't re-test from scratch)

bf16 -25% (carried over from a sibling GPT-350M session on the same system);
ZeRO-1 -20%/+20% regression (confirmed on BOTH transports — not a transport
artifact; ZeRO-1's optimizer-state savings are only 1.4% of HBM on this model
size, so there is no memory pressure to relieve); `TORCH_BLAS_PREFER_HIPBLASLT`
inert; all four `--use-flash-attn*` flags silently no-op (dependency absent —
FlashAttention was never actually exercised, see "Honest gaps" below); kernel
fusion already on by default; NUMA/affinity a measured no-op on the MI300A APU
(unified CPU/GPU memory — reconfirms the same finding seen on IOR/h5bench/
ScaFFold sessions on this system).

#### Honest gaps (do not silently forget these when resuming)

- FlashAttention untested — needs a multi-hour ROCm/CK build; this is the
  highest remaining optimization ceiling for this workload.
- Checkpoint I/O never exercised this session.
- Memory-bandwidth roofline unresolved — no HBM counter available on this
  system.
- `pipeline_plan.md` was never created for this session (a process gap —
  stages were dispatched directly instead of through a written plan).
- Two single-replicate probes (`--log-interval 10`, ZeRO-1-on-libfabric) should
  get a second replicate before being treated as settled.

#### `final_report/` mechanics (useful for future sessions, not Megatron-specific)

- The tool's automated script-glob missed 20+ scripts this session
  (`env.sh`/`env_ofi.sh`/`env_baserocm.sh`, `ab_driver*.sh`, `lever_driver.sh`,
  all `run_ab_*`/`run_ofi_*`/`run_L_*.sh`, `ds_config_bert_*.json`,
  `ab_summarize.py`) — these had to be manually copied into
  `final_report/scripts/` and anonymized (literal alloc id ->
  `${1:?...}`, literal Lustre dataset path -> `${DATASET_ROOT}` sourced from a
  new `config.ini` entry).
- **Re-calling `session_final_report` regenerates `config.ini` from scratch
  every time**, dropping any manually-appended config vars (like
  `DATASET_ROOT`) — re-append after every re-call, before the final privacy
  scan.
- Confirmed the tool's `report_md`/`conversation_md`/`readme_md` params behave
  as: `overwrite=False` + a blank string preserves existing content, but
  `overwrite=False` + non-blank text OR `overwrite=True` always WRITES what you
  pass — there is no "keep existing" placeholder string (passing literal text
  like `"KEEP"` or `"PLACEHOLDER"` overwrites the file with that literal text).
  Always resupply the FULL content in the same call as any other section
  you're fixing.
- `privacy_scan`/`privacy_redact` ran clean at the end of this session (some
  pre-existing findings in unrelated `good-runs/` example snapshots were also
  redacted as part of the same pass, since `privacy_scan` operates
  project-wide, not just over this session's own workspace).

#### Known dangling references (not yet recovered)

This skill's source memory entry referenced two sibling write-ups that do not
currently exist anywhere in project memory or skills:
`software-megatron-deepspeed-compute-tuning-findings` (presumably a deeper
compute-optimization write-up) and `project-megatron-deepspeed-gpt-pipeline`
(a sibling GPT-350M session on the same system, referenced above for the bf16
and transport findings). If a future session locates that content, fold it in
here; do not fabricate it in the meantime.
