# What worked: software_gcc

- [tool:gcc-mpi-pairing] Load compiler module -> load MPI module -> export CC=$(which mpicc) CXX=$(which mpicxx); verify with mpicc --version / mpicxx -v.
