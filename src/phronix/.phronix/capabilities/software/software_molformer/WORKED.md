# What worked: software_molformer

- [molformer/lightning_ddp/run] 1 node, 4 MI300A: `unset PMI_RANK PMI_SIZE PMI_FD PALS_APID PALS_APINFO PALS_NODEID PALS_RANKID PALS_SPOOL_DIR LDCS_RANKINFO`; `flux run -N 1 -n 1 --exclusive <wrapper> python train_pubchem_light.py --gpus 4 ...`; batch=128/GPU, workers=2 -> 1638 samples/s.
- [molformer/lightning_ddp/multinode] 4 nodes / 16 GPUs: all-reduce gate first, then `flux run -N4 -n4 -c 96 -g 4 ... --num_nodes 4 --gpus 4` with MASTER_ADDR/NODE_RANK set by the launch script; DDP init 'Starting with 16 processes' verified.
- [molformer/build/dftracer_hip] `DFTRACER_ENABLE_HIP_TRACING=ON CC=$(which mpicc) CXX=$(which mpicxx) CMAKE_PREFIX_PATH=$ROCM_PATH pip install git+<dftracer>@develop` plus pydftracer @develop; rocprofiler-sdk already in the site ROCm tree.
- [molformer/ray/4node] (2026-08-02) 4 nodes x 4 GPUs, head also a worker (--num-gpus=4), RAY_ADDRESS/DATASET_CSV_PATH/HF_HOME exported everywhere, pinned-revision hf download + single-process pre-warm, join check on 'Ray runtime started.' -> 12 iterations end-to-end.
