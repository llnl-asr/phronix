# What worked: software_pecan

- [pecan/build/venv] Tuolumne, ROCm 6.3.1: module load python/3.11.5; one shared venv; pip install ROCm torch wheels (rocm-rel-6.3.1 manylinux); pip install pyyaml.
- [pecan/build/torch_scatter] copy pytorch_scatter-2.1.2 to a writable dir; PYTORCH_ROCM_ARCH=gfx942 CC=mpicc CXX=mpic++ python setup.py bdist_wheel (ignore trailing Errno 2); pip install dist/*.whl.
- [pecan/build/torch_sparse] copy pytorch_sparse-0.6.18 to a writable dir; module load gcc-native/13; PYTORCH_ROCM_ARCH=gfx942 CC=gcc CXX=g++ python setup.py bdist_wheel; pip install dist/*.whl.
- [pecan/run/flux_ddp] NODELIST=$(flux job info $FLUX_JOB_ID R | python3 -c "import json,sys; print(json.load(sys.stdin)['execution']['nodelist'][0])"); export MASTER_ADDR=$(flux hostlist -n 0 "$NODELIST"); flux run -N4 -n16 -g1 python -u main_app.py <config>.
- [pecan/trace/dftracer_service] export DFTRACER_ENABLE=1 DFTRACER_LOG_FILE=<dir>/trace; flux submit -N<n> -n<n> -c1 dftracer_service start <dir>; poll <dir>/dftracer_server_*.pid; run training; trap: flux submit -N<n> -n<n> -c1 dftracer_service stop <dir>. 2026-07-29.
- [pecan/trace/worker_finalize] top-level _dftracer_worker_init(worker_id) as worker_init_fn: init_dftracer(); atexit.register(finalize_dftracer, logger); chain DYAD init via get_worker_info().dataset. 0/48 empty traces. 2026-07-22.
- [pecan/optimize/io] handle cache + persistent_workers (2026-07-20); decode cache (PECAN_DECODE_CACHE=1) -8.5% epoch-2 (2026-07-22); spawn + num_workers=6 + PECAN_PREFETCH_FACTOR=8 epoch-2 20.27s (-35.7%, 1 rep, 2026-07-22).
- [pecan/trace/ld_preload] LD_PRELOAD=<anaconda3-2023.09>/lib/libstdc++.so.6:<dftracer_prefix>/lib/libdftracer_preload.so keeps GLIBCXX_3.4.32 for torch_scatter/torch_sparse. 2026-07-22.
