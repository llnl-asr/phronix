# What worked: system_dane

- [dane/toolchain/modules] `module load gcc/12.1.1-magic; module load mvapich2/2.3.7; export CC=$(command -v mpicc) CXX=$(command -v mpicxx)` - also survives inside bash -lc (2026-08-27, login node).
- [tool:bank_check] `sacctmgr -nP show assoc user=$USER cluster=dane format=Account,Partition,QOS` and `sshare -U -u $USER`: empty => no bank (2026-08-27).
- [tool:dataset_symlink_check] `readlink -f <session>/dataset && test -d <session>/dataset && echo RESOLVES || echo DANGLES` before any run on dane.
