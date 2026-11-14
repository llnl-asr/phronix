# Lessons: software_megatron_deepspeed

- [L-25ccb3f9] RCCL slow, silently on host TCP sockets -> site aws-ofi-rccl plugin never on LD_LIBRARY_PATH -> add the plugin lib dir to LD_LIBRARY_PATH, leave NCCL_NET unset (-43.1% train_step) (undated)
- [L-14bfecf9] hard failure with NCCL_NET=libfabric, read as plugin ABI incompatibility -> plugin registers as 'AWS Libfabric', name mismatch -> do not set NCCL_NET (undated)
- [L-3f1b32bd] BERT train_step CPU-bound -> inline MLM masking create_masked_lm_predictions on the critical path at --num-workers 0 -> --num-workers 2 (-8.2%) (undated)
- [L-49ded17a] gloo vs nccl showed +1.2%, concluded transport irrelevant -> both backends were on host TCP at the time -> superseded; fix transport before comparing (undated)
- [L-462ee7a3] BERT showed 9x GPT's I/O (7.3% POSIX @ 17.7 MB/s) -> one-off transient Lustre stall: 140.42 s of stat calls -> retracted; re-measured 0.19 ms; voided the contaminated baseline (undated)
- [L-9784d175] bottleneck shares understated ~16x -> percentages computed against dfanalyzer's rank-summed App total (1933.3 s) not per-rank wall (~198 s) -> use per-rank wall time (undated)
- [L-13c36ec8] rocm/6.4.3leakfix credited -4.9% -> single comparison; clean A/B gave -2.2% with overlapping ranges -> keep it for its memory-leak fix, not as a performance claim (undated)
- [L-5bc51fcf] ZeRO-1 regressed -20%/+20% -> optimizer-state savings are 1.4% of HBM at BERT-Base size: no memory pressure to relieve (confirmed on both transports) -> do not enable ZeRO-1 for this model size (undated)
- [L-acae10a6] session_final_report script glob missed 20+ scripts -> glob does not match env*.sh, drivers, ds_config json, summarizers -> copy them into final_report/scripts/ manually and anonymize (alloc id, dataset path) (undated)
- [L-cad6c463] manually appended config.ini vars lost -> re-calling session_final_report regenerates config.ini -> re-append after every call, before the final privacy scan (undated)
- [L-f7752951] report file overwritten with literal 'KEEP'/'PLACEHOLDER' -> non-blank text with overwrite=False is written; no keep-existing placeholder -> blank keeps; otherwise resupply the full content in the same call (undated)
