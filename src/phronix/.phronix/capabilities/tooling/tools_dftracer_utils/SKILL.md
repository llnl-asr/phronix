---
name: tools_dftracer_utils
description: dftracer-utils, the Python binding package for the trace-utils CLI (split, merge, reader, event_count, comparator, aggregator, stats, reconstruct, replay, organize, pgzip, tar on .pfw/.pfw.gz traces): install verification (`import dftracer_utils`), its place in the dftracer / pydftracer / dftracer-utils trio, the session-venv rule, and the known `dftracer_stats --report categories|summary` failure on compacted traces (`No chunk statistics in index for <file>`, `Events processed: 0` from `dftracer_index --rebuild-summaries`) with its workaround. Load before any trace post-processing step (session_split_traces, reader, event_count, comparator, stats) or on a 'dftracer partially works' report.
---
Cross-references: [[tools_dftracer]] [[tools_pydftracer]] [[dftracer_trace]] [[dftracer_analyze]] [[dftracer_install]] [[capability_builder]]

# tools_dftracer_utils

Converted from dftracer-agents skill `tools-dftracer-utils`. Tools: `tools_dftracer_utils_recipe` (predictor) and `tools_dftracer_utils_check` (validator). The structured sections below are the operating rules; the full original skill text follows under 'Source' so no fact, pitfall or dated lesson is lost.

## Rules
- Use the trace-processing MCP tools / dftracer-utils binaries for trace work (split, merge, reader, event_count, comparator, aggregator, stats, reconstruct, replay, organize, pgzip, tar), not raw gzip or ad-hoc scripts; the one sanctioned exception is the category-count workaround below.
- dftracer-utils is a dependency of dftracer (`Required-by: dftracer, dftracer-agents, dftracer-analyzer`): installing dftracer normally installs it.
- Verify with `python -c "import dftracer_utils"` or by running the MCP tool wrapper on a real trace file; do not trust `pip show` alone.
- dftracer (C core), pydftracer (`dftracer.python`) and dftracer-utils fail independently: a working split/event_count/reader does not prove pydftracer is installed; check all three on a 'dftracer partially works' report.
- Never repair the shared framework venv's dftracer-utils in place; install a session-local dftracer (which pulls it in).
- On compacted (split) traces, do not rely on `dftracer_stats --report categories|summary|detailed` or `dftracer_index --rebuild-summaries`: they fail (KNOWN BUG 2026-08-02). Use `event_count` for totals and a full gzip/json parse for category counts.
- On RAW per-rank traces, `dftracer_stats -d <raw_dir> --index-dir <idx> --report categories|top-names` works and is the fastest per-category / per-name count (2026-09-30); re-check the bug before relying on it for compacted traces.
- Category counts must cover all chunks, not a sample: distributions are very uneven (e.g. torch-profiler `PP` events < 0.1%).

## Constraints
- The bug cannot be patched locally: dftracer-utils is a pip-installed prebuilt binary with no local source checkout; the fix belongs upstream (--rebuild-summaries must walk decompressed event content, not only build bloom filters).
- `event_count` (`mcp__dftracer__event_count` / `dftracer_event_count`) is unaffected by the index bug.

## Corner cases
### `No chunk statistics in index for <file>` from `dftracer_stats --report categories` (or summary/detailed) on compacted traces
Cause: `dftracer_index --rebuild-summaries` (and the mcp index wrapper) reports `Events processed: 0`: it builds the bloom-filter existence index (`N total, N cached, 0 failed`) but never scans event content. Not a --checkpoint-size mismatch (default and matched sizes both fail; MCP and raw CLI both reproduce). Workaround: gzip + json parse every chunk counting `cat`. (2026-08-02)

### Split / event_count / reader work but annotated Python fails to import
dftracer-utils and the C core are fine but pydftracer is missing: verify `from dftracer.python import dftracer, dft_fn` separately (see tools_pydftracer).

## Parallel plan

Independent calls go out together in one message: predictor calls on different inputs, and lookups such as knowledge_search or lesson_search, do not depend on each other. Sequential, and why: the validator runs after the predictor whose result it rules on, and the corrector only after the validator's verdict. Larger fan-outs build on [[tools_parallel]] (parallel_plan / parallel_call / parallel_validate).

## Corrector
- Predictor `tools_dftracer_utils_recipe` renders the recipe; validator `tools_dftracer_utils_check` rules on a proposed recipe or command list. Attempts follow measured progress: three to start, more while the failures change; the same failure twice stops the loop for the user.
- `no_stats_report_on_compacted` fails: Use event_count for totals and the full-chunk gzip/json category parse; or run stats on the raw per-rank dir. Then render with `tools_dftracer_utils_recipe` and validate again.
- `no_rebuild_summaries_reliance` fails: Skip it; use event_count / raw-trace dftracer_stats / the category parse. Then render with `tools_dftracer_utils_recipe` and validate again.
- `no_framework_venv_repair` fails: Install a session-local dftracer (session_install_dftracer), which pulls in dftracer-utils. Then render with `tools_dftracer_utils_recipe` and validate again.
- `verify_import_after_install` fails: Run python -c "import dftracer_utils" after the install. Then render with `tools_dftracer_utils_recipe` and validate again.
- `check_trio_not_one` fails: Also run python -c "from dftracer.python import dftracer, dft_fn". Then render with `tools_dftracer_utils_recipe` and validate again.
- If a plan uses stats --report categories on a compacted dir, replace it with event_count for totals plus the full-chunk category parse from tools_dftracer_utils_recipe('category_count_workaround').

## Self-heal
- When a dftracer-utils release fixes --rebuild-summaries (Events processed > 0 on compacted chunks), retire the no_stats_report_on_compacted rule with capability_update and record the version as a lesson.

## Self-learn
- Record each trace-utils failure with the dftracer-utils version and trace form (raw vs compacted) as a dated lesson.
- What is explored here becomes a capability: see capability_builder. A new fact, pitfall or verified recipe for this tool goes into tools_dftracer_utils via capability_update (recipe data and a check rule for what is deterministic, the skill for judgement, a dated LESSONS.md entry for the symptom -> cause -> fix); something that is not about it gets its own workload_/software_/system_/tools_ capability.

## What works
- (2026-09-30) `dftracer_stats -d <raw_dir> --index-dir <idx> --report categories|top-names` on raw per-rank traces: 358 M events indexed and counted in ~70 s with 32 threads.
- (2026-08-02) Category breakdown of compacted traces by a full gzip/json parse of every chunk; event_count for totals.

## Source: dftracer-agents `tools-dftracer-utils` (verbatim, headings demoted)
_Original description:_ dftracer-utils — the Python binding package for the trace-utils CLI (split/merge/compact/reader/event_count on .pfw/.pfw.gz traces). Install verification and its relationship to the dftracer/pydftracer package trio. Load this skill before any trace post-processing step (session_split_traces, reader, event_count, comparator).

#### What it provides

`dftracer-utils` is the PyPI package (`pip show dftracer-utils` →
`Summary: Python binding for dftracer-utils`) backing the trace-processing MCP
tools this project uses for ALL trace work — `split`, `merge`, `reader`,
`event_count`, `comparator`, `aggregator`, `stats`, `reconstruct`, `replay`,
`organize`, `pgzip`, `tar` (see the `dftracer-trace-utils` skill's "always use
the MCP tools, never raw gzip/python scripts" rule). It is a dependency of
`dftracer` itself (`Required-by: dftracer, dftracer-agents, dftracer-analyzer`
on the framework's own venv) — installing `dftracer` normally installs this
transitively.

#### Verification

```bash
python -c "import dftracer_utils"
```
or check the MCP tool wrapper directly succeeds on a real trace file rather
than trusting `pip show` alone.

#### Relationship to dftracer / pydftracer

These are three separate PyPI packages that together make up "the dftracer
ecosystem" for a session:
- **dftracer** — C core, tracing runtime, CMake build. See [[tools-dftracer]].
- **pydftracer** — Python annotation/decorator API (`dftracer.python`). See [[tools-pydftracer]].
- **dftracer-utils** (this skill) — trace post-processing bindings (split/merge/read).

A session can have a working C core and trace-utils (so `session_split_traces`/
`event_count`/`reader` all work fine) while STILL missing `pydftracer` — these
are independent failure modes; verifying one does not verify the others. Check
all three explicitly when diagnosing a "dftracer partially works" report.

#### Session-local vs shared venv

Same rule as [[tools-dftracer]]: never repair the shared framework venv's
`dftracer-utils` in place as a side effect of a session — install a
session-local `dftracer` (which pulls this in transitively) instead.

#### KNOWN BUG (2026-08-02): `stats --report categories/summary` always fails on compacted (split) traces

> Update 2026-09-30: on RAW per-rank traces (`dftracer_stats -d <raw_dir> --index-dir <idx> --report categories|top-names`) it works and is the fastest way to get per-category and per-name counts (358 M events indexed+counted in ~70 s with 32 threads). Re-check this bug on compacted traces before relying on it.

`dftracer_index --rebuild-summaries` (and the `mcp__dftracer__index` wrapper)
reports `"Events processed: 0"` even against multi-hundred-thousand-event
`.pfw.gz` chunks — it builds the bloom-filter existence index (file
resolution/caching works: `dftracer_stats` reports `N total, N cached, 0
failed`) but never actually scans event content to populate per-chunk
statistics. Every subsequent `dftracer_stats --report categories` (or
`summary`, `detailed`, etc.) call then fails per-file with `"No chunk
statistics in index for <file>"` — reproduced both via the
`mcp__dftracer__stats` MCP tool and the raw `dftracer_stats`/`dftracer_index`
CLI binaries directly, with default AND explicitly-matched `--checkpoint-size`
values, so it is not a chunk-size/checkpoint-size mismatch. `event_count`
(`mcp__dftracer__event_count` / `dftracer_event_count`) is unaffected — it
reports a correct total independently of this index path.

**Root cause NOT yet fixed**: no local source checkout of `dftracer-utils`
exists in this project (it's a pip-installed prebuilt binary), so this needs
fixing upstream in the `dftracer-utils` repo's index-building code (the
`--rebuild-summaries` flag needs to actually walk decompressed event content,
not just build bloom filters) — this project can only work around it, not
patch it, until an editable/source install is available.

**Workaround until fixed**: for a category/event-count breakdown, decompress
and parse directly instead of trusting `stats --report categories/summary`:
```python
import gzip, json, collections
cats = collections.Counter()
for line in gzip.open(chunk_path, "rt"):
    line = line.strip().rstrip(",")
    if not line or line in ("[", "]"):
        continue
    try:
        cats[json.loads(line).get("cat")] += 1
    except Exception:
        pass
```
Run across all chunks in the compact dir (not just a sample — category
distribution is very uneven, e.g. `PP` events from a torch-profiler bridge
can be <0.1% of total events and easy to miss with partial sampling).
