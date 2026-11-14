# Lessons: software_posix

- [L-3bfc5d5d] dftracer fails with Code 2001 -> DFTRACER_DATA_DIR=all is only understood by the Python helper layer -> use a real path, e.g. / or /data:/scratch (undated)
- [L-0c5846f4] 4x write regression on VAST -> romio_ds_write=disable on VAST NVMe -> do not disable data-sieving writes on VAST (undated)
- [L-b20fd24c] no optimization proposals for posix_*_ops_slope bottlenecks -> session_generate_optimization_proposals does not support slope metrics -> derive proposals manually from the slope table (undated)
