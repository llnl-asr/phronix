# What worked: software_megatron_deepspeed

- [megatron_deepspeed/bert/run] 4 nodes x 4 GPUs (16 ranks) MI300A, 400 iterations: aws-ofi-rccl lib dir on LD_LIBRARY_PATH, NCCL_NET unset, --num-workers 2; train_step -47.8% replicate-confirmed (noise ~1.9%, n=4). (undated)
- [tool:session_final_report] Pass blank report_md/conversation_md/readme_md with overwrite=False to keep them; re-append manual config.ini vars after every call; copy missed scripts into final_report/scripts/ anonymized; privacy_scan/redact clean. (undated)
