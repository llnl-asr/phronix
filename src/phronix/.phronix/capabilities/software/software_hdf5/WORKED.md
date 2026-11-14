# What worked: software_hdf5

- [hdf5/build/source_ftp] curl -fkL https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.5/src/hdf5-1.14.5.tar.gz; CC=mpicc ./configure --prefix=<ws>/hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production --with-zlib=/usr; make -j && make install; h5cc -showconfig | grep Version: shows 1.14.x. (undated)
- [tool:dftracer_hdf5] cmake -DDFTRACER_ENABLE_HDF5=ON -DHDF5_ROOT=<ws>/hdf5_1.14 for dftracer; export HDF5_DIR and LD_LIBRARY_PATH=<prefix>/lib in every later command; H5F/H5D events appear. (undated)
- [flashx/optimize/lustre_stripe] lfs setstripe -c 16 -S 4M <fresh output dir> before the first checkpoint, striping_unit = 4M, cb_buffer_size a multiple: aggregated writes 1.05 -> 3.76 MB, write time 5.53 s -> 1.45 s at 384 ranks. (2026-07-08)
