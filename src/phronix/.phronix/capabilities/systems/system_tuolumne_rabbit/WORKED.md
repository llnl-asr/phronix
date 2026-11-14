# What worked: system_tuolumne_rabbit

- [tool:flux_alloc_rabbit] Pattern from the source skill (not a dated measurement): `flux alloc -N 1 -q <QUEUE> -t <TIME> -S "#DW jobdw type=xfs capacity=1TiB name=scratch"`, then `export DATA_DIR="$DW_JOB_scratch"` in the wrapper script run by `flux proxy <JOBID> bash <ws>/tmp/<script>.sh`.
