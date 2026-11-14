# Lessons: software_mpifileutils

- [L-c3c82960] verified move reported byte mismatch on every directory though file counts matched (nothing deleted) -> du -sb --apparent-size counts directory inodes, sized differently on NFS vs VAST (12288 B per 2 dirs; 111 MB for 1756 dirs) -> compare regular-file bytes via find -printf '%s', file counts, and rsync --dry-run --itemize-changes (or dcmp) (2026-08-27)
- [L-6531ee83] `ml mpifileutils` fails -> two versions installed (0.11.1, 0.12), ambiguous default -> module load mpifileutils/0.12 (undated)
- [L-39956471] copy appears to corrupt traces -> pre-existing truncation from a killed run surfaces at the destination -> check the source before deleting it; distinguish copy damage from source damage (undated)
