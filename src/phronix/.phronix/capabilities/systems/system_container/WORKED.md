# What worked: system_container

- [tool:mpirun] `command -v mpirun || sudo apt-get install -y openmpi-bin libopenmpi-dev`, then `mpirun -n <N> ./app` from workspaces/<session>/.
