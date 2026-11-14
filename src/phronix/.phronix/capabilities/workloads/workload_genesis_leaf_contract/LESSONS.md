# Lessons: workload_genesis_leaf_contract

- [L-4e1a7c93] Published leaves carried a stale COMPACTION_NOT_RUN.md, 2 of 9 validation_*.json, and summary.json with hosts: [], all passing a human read-through -> prose contract with no deterministic checker -> enforce the seven clauses with genesis_validate_leaf.py --sets=N before declaring a corpus complete (2026-10-21)
- [L-b83f0d52] Every compacted leaf reported as missing its run/validation records -> checker only looked in raw/, which is reclaimed after compaction -> look in raw/ and at the leaf top level (2026-10-21)
- [L-2c9d6e17] COMPACTION_NOT_RUN.md stamped onto already-compacted leaves on a real publish -> chunks live at the leaf top level (app-<n>_chunk0.pfw.gz), not in compacted/ -> detect chunks at top level OR compacted/ (2026-10-21)
- [L-71f05ab8] A green checker run trusted without falsification -> a checker that only passes is worthless -> verify every clause against a deliberately broken copy of a good leaf (summary deleted, data deleted, note beside chunks, multiplex={1:5}/app_files=1) and re-run on every checker edit (2026-10-21)
