# What worked: system_tioga

- [tool:dftracer_split] Tuolumne-built dftracer_split runs unmodified on tioga; post-process a Tuolumne corpus here (traces live in the shared NFS workspace).
- [genesis/flux/cores_per_rank] With dftracer_service on every node, ppn=8 at -c 7 schedules; -c 8 sits S forever.
- [tioga/flux/preflight] `flux queue list; flux queue status; flux resource list`, then a throwaway `flux alloc -q <queue> -N1` before sizing a sweep.
