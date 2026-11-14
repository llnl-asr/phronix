---
name: workload_genesis_leaf_contract
description: The published-leaf contract for a genesis trace corpus - exactly which artifacts every leaf in the shared archive must carry (data, COMPACTION_NOT_RUN.md, summary.json, run_<set>.json, validation_<set>.json), why each clause exists, and the deterministic checker that enforces it. Load before publishing a leaf, before declaring a corpus complete, whenever two sweeps must be consistent, or on "FAIL <leaf>", "stale COMPACTION_NOT_RUN.md", "PAPI multiplexed (estimates)", "app_files != ranks".
---
Cross-references: [[workload_genesis_run]], [[software_papi]], [[software_mpifileutils]], [[tools_dftracer_utils]], [[system_tuolumne]]

# workload_genesis_leaf_contract

A genesis corpus is published leaf by leaf, often across many allocations, several machines and more than one sweep.
Without an enforced contract each round quietly publishes slightly less than the last, and the gaps are only discovered
by whoever tries to *use* the corpus - long after the nodes that could have fixed it are gone.

**This capability is the contract plus its checker.** Prose alone has already failed here: leaves were published with a
stale `COMPACTION_NOT_RUN.md`, with 2 of 9 `validation_*.json`, and with `summary.json` reporting `hosts: []`. Every one of
those passed a human read-through and would have shipped. Converted from dftracer-agents' `genesis_leaf_contract` skill;
the original checker script is kept verbatim in `docs/scripts/genesis_validate_leaf.py`.

Tools: `workload_genesis_leaf_contract_recipe` (predictor: the contract as JSON), `workload_genesis_leaf_contract_check`
(validator: a proposed publish/finalize command list), `workload_genesis_leaf_contract_leaf_check` (validator: the published
leaves on disk, in-process port of the script).

## Rules
Every directory matching `<archive>/<case>/nodes_<N>/ppn_<P>/` must satisfy ALL of:

| clause | requirement |
| --- | --- |
| **DATA** | at least one copy of the traces - compacted chunks (`*.pfw.gz` at the leaf top level or in `compacted/`) **or** `raw/papi_*/**.pfw.gz` |
| **NOTE** | no chunks => `COMPACTION_NOT_RUN.md` **must** exist; chunks => it **must not** |
| **SUMMARY** | `summary.json` present, parseable, its `leaf` ending in this cell's own `<case>/nodes_<N>/ppn_<P>`, and `ranks == nodes*ppn` |
| **RUN JSON** | one `run_<set>.json` per validated PAPI set |
| **VALIDATION** | one `validation_<set>.json` per set |
| **EXACTNESS** | every run record reports `multiplex` of exactly `0` |
| **COMPLETE** | every run record reports `app_files == ranks` |

Why each clause is there, not just what it says:
- **DATA** - a leaf with neither chunks nor `raw/` is an empty directory impersonating data. It happens when a publish is
  interrupted between `mkdir` and the copy.
- **NOTE** - both directions matter equally. A missing note on an uncompacted leaf leaves a reader no way to know `raw/` is
  the authoritative copy. A *stale* note on a compacted leaf makes a finished leaf look unfinished, which is how work gets
  needlessly redone.
- **SUMMARY `leaf` and `ranks`** - catches a `summary.json` copied from another cell, or generated against the wrong
  `(nodes, ppn)`. Both are easy to produce and invisible without the cross-check.
- **RUN JSON** - one leaf is N runs (one per PAPI set). `summary.json` aggregates them, so it cannot say *which* run
  multiplexed or *which* lost a rank. Without the per-run record a defect is detectable but not locatable.
- **EXACTNESS** - `multiplex != 0` means PAPI time-shared the counters and the values are **scaled estimates**, not
  measurements. dftracer reports this in the trace but nothing refuses it; the corpus looks healthy and the numbers are wrong.
- **COMPLETE** - `app_files < ranks` is a missing rank. No later processing can reconstruct it, so it must fail at publish
  time, while a rerun is still cheap.

The checker:
```bash
genesis_validate_leaf.py <archive_root> [--sets=N] [--json]
```
Exits `0` only when every leaf passes; prints one `FAIL <leaf>: <reasons>` line per violation. `--sets=N` additionally
asserts each leaf carries N run records (the size of this machine's PAPI partition), which catches a leaf that sealed early.
Run it **before declaring a corpus complete**, and after any publish round (or call `workload_genesis_leaf_contract_leaf_check`).
```bash
# measured on the amg/tuolumne corpus
$ genesis_validate_leaf.py .../dftracer-traces/amg/tuolumne --sets=9
343/343 leaves satisfy the published-leaf contract
```

## Constraints
- **A checker that only ever passes is worthless - prove it fails.** Never trust a green run you have not falsified. Each
  clause was verified against a deliberately broken copy of a good leaf:

  | control | expected | result |
  | --- | --- | --- |
  | verbatim good leaf | pass | `1/1 satisfy` |
  | `summary.json` deleted | fail | `missing summary.json` |
  | chunks **and** `raw/` deleted | fail | `no data: neither compacted chunks nor raw/ traces` |
  | note added beside chunks | fail | `compacted but stale COMPACTION_NOT_RUN.md present` |
  | run record set to `multiplex={1:5}`, `app_files=1` | fail | `PAPI multiplexed (estimates)`; `app_files 1 != ranks 2` |

  Re-run these controls whenever a clause is added or the checker is edited.
- Do not hand-review leaves instead of running the checker.
- **Match the archive's existing shape before inventing a new one.** `summary.json` is the established per-leaf file
  (`laghos/*` publishes it; its key names are what consumers read). `run_<set>.json` is an addition, not a replacement.
  Check a neighbouring app's published leaves before adding any new file to a corpus - a parallel convention is worse than
  a slightly imperfect shared one.
- The tools only read file names and the small JSON records; they never move, compact or delete data.

## Corner cases
Where the artifacts live, and the two traps:
- `run_<set>.json` and `validation_<set>.json` live **inside `raw/`** so they travel with the traces they describe. When
  `raw/` has been reclaimed after compaction they sit at the **leaf top level** instead. **A checker must look in both** -
  one that only checks `raw/` reports every compacted leaf as missing its records.
- Compacted chunks in this archive are at the **leaf top level** (`app-<n>_chunk0.pfw.gz`), *not* in a `compacted/`
  subdirectory. Checking only for `compacted/` wrongly stamps `COMPACTION_NOT_RUN.md` onto leaves that are already
  compacted - measured, on a real publish.
- A run record with `status: SKIPPED` is exempt from EXACTNESS/COMPLETE (structurally impossible cell, see
  [[workload_genesis_run]] STEP 10b).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
`workload_genesis_leaf_contract_leaf_check` names, per failing leaf, the clause and a fix; repair, then re-check:
- `no data` -> the publish was interrupted: republish that leaf (genesis_publish.sh).
- `uncompacted but no COMPACTION_NOT_RUN.md` -> write the note with the reason, saying `raw/` is authoritative.
- `compacted but stale COMPACTION_NOT_RUN.md present` -> delete the stale note.
- `missing summary.json` / `summary.leaf mismatch` / `summary.ranks ... != nodes*ppn` -> regenerate `summary.json` for THIS cell.
- `no run_<set>.json` / `only K run_*.json, expected N` -> backfill run records (reconstruct from `state_*`,
  `artifacts/<key>.log`, `validation_<set>.json`, `null` for the unavailable, `backfilled: true`), or unseal the leaf and run
  the missing sets.
- `PAPI multiplexed (estimates)` -> rerun that set with a smaller probe-verified set ([[workload_genesis_run]] STEP 6).
- `app_files K != ranks R` -> a rank is missing: rerun that set.
`workload_genesis_leaf_contract_check` failures: `validate_before_complete` -> run the checker first; `sets_asserted` -> add
`--sets=N`; `no_compacted_only_note` -> decide the note from top-level OR `compacted/` chunks; `no_hand_perms` -> use the
archive's `chgperm.sh`. Then render and validate again; the same failure twice stops the loop for the user.

## Self-heal
If the checker passes a deliberately broken leaf (a negative control above), the checker is wrong: fix it here
(`capability_update`) and in `docs/scripts/genesis_validate_leaf.py` together, re-run every control. `lesson_search` a FAIL
reason first.

## Self-learn
What is explored here becomes a capability: a new clause found necessary (a defect that shipped past the checker) is added
to the contract, the checker and the negative-control table together via `capability_update`; each new
symptom -> cause -> fix goes to LESSONS.md and verified publish rounds to WORKED.md.

## What works
- 2026-10-21 (recorded): `genesis_validate_leaf.py <archive>/amg/tuolumne --sets=9` -> `343/343 leaves satisfy the
  published-leaf contract`; all five negative controls fail as expected.

## Related
[[workload_genesis_run]] - STEP 12 defines the publish order and both metadata schemas.
