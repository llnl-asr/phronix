---
name: workload_1000genome
description: 1000genome-workflow (pegasus-isi/1000genome-workflow) - Pegasus/PMC execution, pure-Python task scripts, annotation pitfalls (module-level tar I/O, daxgen.py), run sizing (3.9 h README baseline), the measured individuals.py optimization (IND_ROW_PRECOMPUTE, IND_TAR_STREAM, 1.29x workflow), the session_annotation_report false 0/0 and the pair_individuals upstream bug. Load for 1000genome, individuals.py, mutation_overlap.py, frequency.py, sifting.py.
---
Cross-references: [[software_pegasus]], [[tools_pydftracer]], [[software_flux]], [[system_tuolumne]], [[tools_dftracer]]

# workload_1000genome

Converted from dftracer-agents' `workload-1000genome` (cross-references there: dftracer-software-pegasus, software-pegasus,
dftracer-annotation-lessons, flux-alloc). `workload_1000genome_recipe` renders the recipe; `workload_1000genome_check` rules on
a proposed command list.

## Rules

### What this workflow is
A Pegasus scientific workflow analyzing 1000 Genomes Project VCF (Variant Call Format) data: SNP frequency filtering, SIFT
scoring, and pairwise mutation-overlap analysis across individuals/populations. Unlike Montage (compiled C, single binary
type), every task here is a standalone Python script under `bin/`:
- `individuals.py`: **dominant cost, 81.85% of baseline wall time** per the README. Parses VCF files by chromosome, filters SNPs
  by allele frequency, writes one output file per individual, tars the results.
- `individuals_merge.py`: merges per-job tar.gz chunks for a chromosome.
- `sifting.py`: reads VEP (Variant Effect Predictor) score files, writes scored SNP lists.
- `mutation_overlap.py`: untars chromosome data, reads population CSVs, computes pairwise SNP overlap between individuals,
  writes PNG heatmaps.
- `frequency.py`: random-sampling overlap-frequency analysis, matplotlib PNG output.
- `individuals_mpi.py` / `individuals_merge_mpi.py`: MPI variants, not part of the default PMC task set; left unannotated unless
  specifically needed.
- `daxgen.py`: the workflow generator itself (produces the Pegasus DAX/YAML). Never runs as a traced task under PMC: exclude
  from annotation.

### Execution architecture
Same PMC-only pattern as Montage: see [[software_pegasus]] (dftracer-software-pegasus) for the full
Condor(planning-only)/Pegasus-5.0.7/PMC-from-source install recipe. No workflow-specific deviations found; the generic Pegasus
skill applies as-is. Default project docs point at HTCondor `condorpool`/Cori-Bosco/Decaf execution modes: ignore these, use
PMC per this project's standing convention (no site-wide Condor pool on Tuolumne).

### Baseline run sizing
README reports single-chromosome, 10-individuals-jobs baseline at **~3.9 hours** (individuals: ~11,400 s / 81.85%, frequency:
10.68%, rest ~5%). Far too long for a bounded pipeline smoke/baseline run: scope down via `prepare_input.sh` options and/or
`daxgen.py -i <num_individuals_jobs>` to target a ~10-20 minute run (fewer individuals-jobs and/or a reduced VCF row count),
consistent with this project's run-sizing convention for other workloads.

### Annotation notes
- Pure Python FUNCTION-mode annotation via `python_annotate_project` / `python_annotate_file` works cleanly on all 5 target scripts.
- **Module-level (script-scope) I/O**: `mutation_overlap.py` and `frequency.py` each execute a top-level
  `tarfile.open()/extractall()/close()` block outside any function: no decorator tool can reach this. See
  `dftracer-annotation-lessons` PP9 for the manual `with DFTracerFn(...):` fixup pattern.
- `individuals.py` annotation should prioritize the VCF read loop and the per-individual file-write + tar-compress path: that's
  where the 81.85% of wall time lives.

### Optimization (STEP 8/9, 2026-07-26): individuals.py I/O + compute fix
`individuals.py` had a genuine algorithmic defect: an `O(rows x individuals x ncols)` per-individual loop recomputing
row-invariant VCF-parse work for every one of 2504 individuals, plus a `compress()` step that wrote per-individual scratch files
then reopened/re-read every one of them into a tar archive (write-then-reopen round trip). Two composed fixes, both behind env
gates defaulting to OFF (baseline path bit-for-bit unchanged, measured +0.3% i.e. noise, when gates are off):
- `IND_ROW_PRECOMPUTE=1`: hoists all row-invariant VCF-parse work into a single `precompute_rows()` pass, plus a compact
  1-byte/individual allele string. **-93.4% standalone** (90.65 s -> 6.00 s median, n=5, disjoint ranges).
- `IND_TAR_STREAM=1`: in-memory `tarfile.addfile(TarInfo, BytesIO)` streaming, removing 2504 scratch create/stat/read/unlink
  calls per task. Composed with the above: **-99.5% (193x) standalone** (90.65 s -> 0.47 s median, n=5).
- Also applied unconditionally: removal of `chrp_data`, a dead write-only accumulator (-25.8% peak RSS, wall-neutral,
  byte-identical output).
- `gc.disable()+gc.freeze()` was tried and REJECTED: **+1.7% regression** (acyclic object graph, see dftracer-memory-optimization).

**Correctness verification method** (reproducible; use this pattern for any per-file-fan-out optimization): extract the output
tar member-by-member for each configuration and compare against the pristine baseline's extracted members via per-member md5:
**2504/2504 members identical** across gates-off, `IND_ROW_PRECOMPUTE=1` alone, and both gates combined. Also ran `diff -rq` over
all 2504 per-individual output files (no differences) and traced the code line-by-line to confirm preserved edge-case semantics
(e.g. the AF string vs. float distinction, the `split(';')[8]` IndexError location, per-row `float()` ValueError skip behavior)
held identically before and after.

**Workflow-level (DAG, 4-node PMC) result:** 316.5 s -> 244.7 s, **1.29x (29.3%), 71.8 s saved**, 46/46 tasks succeeded. This is
well below the 193x standalone task-level number BY DESIGN, not a partial win: `individuals.py` is 82% of task work (hard
ceiling), and the DAG's own critical-path structure (level-4 `individuals_merge` is a hard width-1 serialization barrier; levels
5-7 including `frequency`/`mutation_overlap` were untouched) re-dominates the makespan once `individuals` collapses. The
optimizer's own pre-run prediction ("workflow-level gain will be much smaller than the standalone number, capped by the merge
barrier and untouched downstream tasks") was confirmed by the measured 29.3%. Always compute DAG critical-path structure (level
widths from the `.dag` file) BEFORE predicting a workflow-level speedup from a task-level fix: see
dftracer-communication-optimization's DAG-max-width rule.

## Constraints
- **Known upstream bug, reported not fixed (do NOT fix: would change results).** `mutation_overlap.py`'s `pair_individuals`
  function was found (STEP 8 optimizer review) to include self-intersections when building individual pairs, i.e. an individual
  can be paired against itself in the overlap computation, very likely an upstream logic bug in the original 1000genome-workflow
  repo, not something introduced by this session's annotation or optimization work. It was deliberately left UNFIXED: fixing it
  would change the numerical output of `mutation_overlap.py` (a correctness-affecting change, not a performance optimization),
  which is out of scope for a dftracer optimization pipeline and would break the apples-to-apples baseline/optimized comparison.
  Reported here for visibility if a future session works on this app's correctness rather than its performance.
- Optimizations stay behind env gates defaulting to OFF so the baseline path is bit-for-bit unchanged.
- The recipe/check tools render and check text only; they never run a workflow.

## Corner cases
- **Resolved tool bug: `session_annotation_report` false 0/0.** It returned `0/0 functions (0.0%)` for this app despite real
  annotations under `annotated/bin/*.py`. Root cause: an unmodified full clone was also left behind at `annotated/source/` (87
  files, identical content to `source/`); the tool's `_resolve_annotated_root` picked the candidate root by raw file-existence
  overlap (87 > 5) instead of actual edits, so it diffed identical trees and found nothing. Fixed in `_count_counterparts`
  (`src/dftracer_agents/mcp_tools/tools/session/annotation.py`) to score candidate roots by content-differs-from-source, not path
  overlap. After the fix: 5/5 files, 38/38 functions, 100% coverage. If a future session sees a similarly-wrong `annotated/`
  root pick, check for leftover unmodified clones sitting alongside the real annotated output directory.
- Module-level tar I/O in `mutation_overlap.py`/`frequency.py` is invisible to decorator tools: wrap by hand (PP9).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
For each failed check of `workload_1000genome_check`, repair the proposed commands, then call `workload_1000genome_recipe` and the check again:
- `no_condor_pool`: plan with Condor planning-only, execute with PMC (software_pegasus).
- `no_annotate_daxgen`: drop daxgen.py (and the *_mpi.py variants) from the annotation target list.
- `no_fix_pair_individuals`: revert any change to pair_individuals; report only.
- `no_gc_freeze`: drop gc.disable()/gc.freeze().
- `sized_run`: add `daxgen.py -i <n>` / `prepare_input.sh` scoping for a ~10-20 min run.
- `input` (inconclusive): pass the command list. The same failure twice stops the loop for the user.

## Self-heal
On a failed task or a wrong coverage report match it to Corner cases and LESSONS.md (`lesson_search` the error first); if a rule
here is wrong, `capability_update` this capability with the evidence.

## Self-learn
What is explored here becomes a capability: a new 1000genome procedure (sizing, annotation fixup, optimization) verified by hand
is added here (`capability_update`); Pegasus/PMC facts go to software_pegasus; each error -> cause -> fix goes to LESSONS.md and
each verified recipe to WORKED.md.

## What works
- 2026-07-26: `IND_ROW_PRECOMPUTE=1 IND_TAR_STREAM=1` on individuals.py: 90.65 s -> 0.47 s per task (193x), 2504/2504 tar members
  md5-identical; 4-node PMC DAG 316.5 s -> 244.7 s (1.29x), 46/46 tasks succeeded.
- python_annotate_project on the 5 target scripts + PP9 `with DFTracerFn(...):` around the module-level tar blocks: 5/5 files,
  38/38 functions, 100% coverage.
