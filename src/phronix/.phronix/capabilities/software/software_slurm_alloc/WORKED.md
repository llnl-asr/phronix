# What worked: software_slurm_alloc

- [slurm/alloc/test_only] sbatch -p <part> -N<n> -t <min> --gres=gpu:4 --test-only --wrap=hostname per candidate shape; pick the shape that starts soonest and still fits the time limit. (undated)
- [slurm/run/daemon_step] Daemon as a long-lived --overlap --nodelist step waiting on a STOP_FLAG and on non-empty output; app in a separate --overlap step on the same slice under timeout + --kill-on-bad-exit=1; touch STOP_FLAG; wait. (undated)
