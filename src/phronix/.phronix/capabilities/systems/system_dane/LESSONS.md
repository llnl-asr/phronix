# Lessons: system_dane

- [L-eb7dd330] Every sbatch, including --test-only, fails 'Invalid account or account/partition combination specified' -> No Slurm association (bank) for the user on dane -> Check sacctmgr/sshare first; request a bank; do not debug partitions (2026-08-27)
- [L-12e3b5d0] Probe code reports an NVIDIA GPU on dane; nvidia-smi fails 'couldn't communicate with the NVIDIA driver' -> /usr/bin/nvidia-smi ships in the TOSS image; no GPU present -> Key on a working device, never file existence; never enable CUDA tracing (2026-08-27)
- [L-d1a3486d] system_detect power probe reports gpu: rocm_smi (/opt/rocm-7.2.0) -> Complete /opt/rocm-6.4.3 and 7.2.0 userspaces installed without an AMD device -> systems.yaml tracing.power: off; never enable HIP tracing (2026-08-27)
- [L-aac1ccb5] ppn ladder over-subscribes nodes 2x -> lscpu CPU(s): 224 counts offline SMT siblings -> Use nproc = 112 (2026-08-27)
- [L-08ac1184] papi/6.0.0.1 shows 0 counters, 0 presets -> Module predates Sapphire Rapids -> Use system libpapi.so.5 5.6.0.0; tracing.papi_module "" (2026-08-27)
- [L-c8780e34] Zero power events in every trace -> MSR root-only/no msr_safe, RAPL energy_uj 0400, PAPI rapl unsupported, no GPU -> tracing.power off, DFTRACER_DISABLE_VARIORUM_POWER=1, state it in the corpus README (2026-08-27)
- [L-58db4cee] Science audit reports 'no result file' while traces are fine -> dataset symlink onto /p/lustre5, which dane does not mount -> Per-system dataset symlink onto /p/lustre1..3; check RESOLVES before running (2026-08-27)
- [L-1d9165fb] matrix's bash -lc module rollback assumed on dane -> The rollback is matrix-specific, not TOSS-wide -> Module loads in bash -lc survive on dane; still verify with which (2026-08-27)
