# Lessons: software_slurm_alloc

- [L-af335ab2] multi-node srun/sbatch rejected with 'Invalid generic resource (gres) specification' / 'Requested node configuration is not available' -> partition MaxNodes=1 (matrix-class pdebug, 2 nodes total) -> check scontrol show partition MaxNodes before planning (undated)
- [L-515e646e] pending with Nodes_required_for_job_are_DOWN,_DRAINED_or_reserved_for_jobs_in_higher_priority_partitions -> partitions share nodes; the higher-priority one holds them -> compare sinfo node lists; not a hardware fault (undated)
- [L-d7d0c3a7] bigger allocation waited a half-day -> start estimate depended on node count, not walltime (2 nodes: same day; 4: +13 h; 8: +14 h) -> measure with sbatch --test-only; request exactly the nodes needed (undated)
- [L-99f79e3d] helper daemon 'ran' but produced nothing (rc 0, pid file) -> daemon is a child of its job step and is reaped when the step ends -> run it as a long-lived step waiting on a stop flag (undated)
- [L-849f0507] daemon output truncated / 0-byte after stop -> asynchronous flush after stop; step exit reaps it mid-flush -> wait for non-empty output before the step exits (undated)
- [L-a15bd957] cudaErrorInvalidDevice under --gpus-per-task -> single visible device renumbered to 0; app selects SLURM_LOCALID % n -> use --gres=gpu:4 or adapt device selection; verify per task (undated)
- [L-354094a6] sweep hung after one rank aborted -> peers block in the next collective forever -> timeout + srun --kill-on-bad-exit=1 (undated)
- [L-575f5e01] app ran without env vars meant for it -> trailing backslash followed by a comment line ended the command -> ( export FOO=1 BAR=2; srun ... ) (undated)
- [L-18f20790] modules rolled back inside bash -lc -> login profile reloads site defaults -> sourced module script; verify with which (undated)
- [L-1661e5f0] set -e caller killed silently by a sourced env script -> trailing [ -d ] && source returned 1 -> end env scripts with true (undated)
- [L-10d4953b] pkill -f killed the cleanup command itself -> pattern matched the invoking shell's command line -> filter by pid and /proc/<pid>/cmdline (undated)
- [L-6b572126] sweep checkpointed units that produced nothing -> runs return rc=0 with mis-set env / reaped daemon / tracing off -> checkpoint only after counting non-empty artifacts (undated)
