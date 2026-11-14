---
name: workload_ygm
description: DEPRECATED redirect stub - YGM content is split between software_ygm (the YGM library itself, annotated BY dftracer) and workload_ygm_bench (ygm-bench, the traced benchmark that exercises YGM, analogous to workload_ior/workload_h5bench). Exists only to redirect old references to workload-ygm.
---
Cross-references: [[software_ygm]], [[workload_ygm_bench]], [[workload_ior]], [[workload_h5bench]]

# workload_ygm

**This capability is deprecated and split in two.** Converted from dftracer-agents' deprecated `workload-ygm` stub.
`workload_ygm_recipe` returns the redirect; `workload_ygm_check` refuses content aimed here.

## Rules
Load whichever fits:
- **[[software_ygm]]**: the YGM library itself: annotation caveats (header-only + split `.ipp`, include order), build/CMake
  linkage to dftracer, Cray-clang-vs-spdlog compiler pitfall, smoke test. YGM is annotated BY dftracer, not a traced scientific
  workload, hence `software_*` naming per feedback-software-vs-workload-naming.
- **[[workload_ygm_bench]]**: ygm-bench (github.com/llnl/ygm-bench), the actual traced BENCHMARK run against the annotated YGM
  tree: build steps, the hot-loop over-annotation + selective-aggregation fix, `MPI_Iallreduce` rank-density collapse, irecv buffer
  OOM/env-var-name pitfall, and the confirmed >=10-minute scaled-run reference config. Same `workload_*` pattern as
  `workload_ior`/`workload_h5bench`: ygm-bench is a benchmark workload, not a library dftracer instruments.

## Constraints
- Do not re-add content here: edit `software_ygm` or `workload_ygm_bench`, matching which one actually owns the fact.

## Corner cases
- History: originally reconciled 2026-08-04 during the ygm/20260804_221748 session's final report pass into a single
  `software-ygm` file; split again the same day per user correction (ygm-bench deserves its own workload skill, same as IOR/h5bench,
  rather than being folded into the library's skill).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
`workload_ygm_check` fails with `no_library_facts` -> move the content to software_ygm; with `no_bench_facts` -> move it to
workload_ygm_bench (capability_update there), then check again. `input` (inconclusive): pass the proposed lines.

## Self-heal
If something still loads this stub for real work, follow the redirect; if a reference keeps pointing here, fix the referrer.

## Self-learn
What is explored here becomes a capability: but not this one. New YGM facts become part of software_ygm or workload_ygm_bench
(capability_update), new software met on the way its own `software_<x>`.

## What works
- Nothing is run from this stub; the verified recipes live in workload_ygm_bench (WORKED.md) and software_ygm.
