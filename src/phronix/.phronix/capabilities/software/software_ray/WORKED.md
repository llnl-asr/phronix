# What worked: software_ray

- [ray/multinode/start] export LD_PRELOAD=""; ray start --head --port=<port> (full device counts); on each worker export LD_PRELOAD=""; ray start --address=<head_ip>:<port>; driver exports RAY_ADDRESS; workers wait on a head-written completion marker before ray stop. (undated, Ray 2.48.0, ROCm 6.2.1)
- [ray_molformer/analyze/spill_filter] Read events via TraceViewer, drop records containing default_worker.py, then match '<ray_temp_dir>' to separate real object-store spill I/O from worker cmdline strings. (2026-08-02)
