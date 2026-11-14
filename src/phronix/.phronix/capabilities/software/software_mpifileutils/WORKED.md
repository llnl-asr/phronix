# What worked: software_mpifileutils

- [tool:dwalk] module load mpifileutils/0.12; flux run -n 8 -q pdebug dwalk --text <tree> gives file count and size histogram before committing to an operation. (undated)
- [mpifileutils/move/verify] filebytes() { find "$1" -type f -printf '%s\n' | awk '{s+=$1} END{print s+0}'; }; compare filebytes and file counts of src/dst, then rsync -a --dry-run --itemize-changes src/ dst/ | grep -cE '^[<>ch]' must be 0; delete source only after. (2026-08-27)
