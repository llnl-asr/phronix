# What worked: software_pegasus

- [montage/pmc/run] Montage 1 degree dss:DSS2B:blue via montage-workflow-v3: pegasus-plan --conf pegasus.properties --sites local --dir work --output-site local data/montage-workflow.yml; flux proxy <alloc> flux run -N1 -n8 bash pmc_wrapper.sh <pegasus>/bin/pegasus-mpi-cluster -v <run>/<name>-0.dag -> 57/57 tasks succeeded, one trace per annotated-binary invocation (mProject/mProjExec largest).
- [tool:pegasus-mpi-cluster] Rebuilt from pegasus 5.0.7 source packages/pegasus-mpi-cluster with make CXX=$(which mpicxx) prefix=<pegasus> against Cray MPICH 9.0.1 (crayclang), ~10 s.
