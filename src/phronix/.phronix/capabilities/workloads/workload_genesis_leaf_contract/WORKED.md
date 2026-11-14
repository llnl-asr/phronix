# What worked: workload_genesis_leaf_contract

## genesis/publish/leaf-contract
After each publish round and before writing README.md: `genesis_validate_leaf.py <archive>/<app>/<system> --sets=<N PAPI sets>`
(script in docs/scripts). Measured on amg/tuolumne with --sets=9: 343/343 leaves satisfy the contract (2026-10-21).

## genesis/publish/negative-controls
Copy one good leaf to a scratch archive and break it five ways (delete summary.json; delete chunks and raw/; add a note beside
chunks; set a run record to multiplex={1:5}, app_files=1): each must FAIL with the clause's message; the verbatim copy passes 1/1.

## tool:workload_genesis_leaf_contract_leaf_check
In-process port of the script: `workload_genesis_leaf_contract_leaf_check(archive_root=<archive>/<app>/<system>, sets=<N>)`
returns status pass|fail and one check per leaf with the failing clauses and their fixes.
