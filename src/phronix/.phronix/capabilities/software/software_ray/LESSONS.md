# Lessons: software_ray

- [L-e8d01b28] `ray start --head` fails after ~35 s with gcs_server.err FileNotFoundError and GCS connect/cluster-ID timeouts -> Ray injects LD_PRELOAD=libjemalloc.so when LD_PRELOAD is unset; dlopen fails with 'cannot allocate memory in static TLS block' on Cray PE + module load rocm, gcs_server never reaches main() -> export LD_PRELOAD="" before every ray start (head and workers) (undated)
- [L-e6f0b859] multi-node Ray Train job hangs forever at ~0% CPU -> ray.init() without RAY_ADDRESS created an isolated single-node cluster -> set RAY_ADDRESS in the driver's environment (undated)
- [L-17c04f18] cluster under-resourced vs ScalingConfig -> --num-gpus=0/--num-cpus=0 passed reflexively to a compute-node head -> let the head contribute its full device count (undated)
- [L-f6e44624] worker processes (and GPUs) disappear before the head job finishes -> fixed sleep N before ray stop races job duration -> poll a head-written completion marker with a generous upper bound (undated)
- [L-66afe2de] POSIX metadata bursts at epoch boundaries in ray.data training (MoLFormer, 2-node, 4 epochs) -> not dataset re-reads (CSV: 9 ops / 0.006 s, driver only); 117,920 __lxstat64 from worker site-packages import walks -> resolve FH paths before proposing dataset caching/striping (undated)
- [L-f85357a6] trace grep suggests object-store spilling -> default_worker.py cmdlines embed --object-store-name=.../plasma_store -> grep -v default_worker.py first; ray_molformer: 337 ops, zero spill (2026-08-02)
