# What worked: workload_gromacs

## gromacs/build/configure
CMake 3.29.2 (`module load cmake/3.29.2`), `cmake -S source -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -DGMX_MPI=ON -DGMX_GPU=HIP
-DGMX_OPENMP=ON -DGMX_DOUBLE=OFF -DBUILD_TESTING=OFF -DGMX_BUILD_HELP=OFF -DGMX_BUILD_MANUAL=OFF -DGMX_INSTALL_LEGACY_API=ON
-DHDF5_DIR=<session_hdf5_prefix>` with the Cray MPICH mpicc/mpicxx as MPI_C/CXX_COMPILER; install completes (2026-08-07, Tuolumne).

## gromacs/build/hdf5
HDF5 1.14.3 from source: `CC=mpicc ./configure --prefix=<ws>/hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production
--with-zlib=/usr && make -j8 && make install`, then `sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/'
<prefix>/include/H5Apublic.h` (2026-08-07).

## tool:workload_gromacs_recipe
Renders the above as JSON; `workload_gromacs_check` passes a configure line carrying -DGMX_BUILD_MANUAL=OFF and -DGMX_BUILD_HELP=OFF.
