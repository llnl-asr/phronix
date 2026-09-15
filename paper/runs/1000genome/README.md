# eval5 — 1000genome

Collected 2026-09-15 16:36. Everything here was produced by
`paper/figures/eval5_collect.py`; nothing is transcribed by hand.

* application: `https://github.com/pegasus-isi/1000genome-workflow @ master`
* dataset: `/p/lustre3/haridev/1kg-eval/data`
* smoke test: `python3 bin/individuals.py ALL.chr1.tiny.vcf 1 0 300 300`

## Runs

| | bare | phronix |
|---|---|---|
| finished | False | False |
| turns | 0 | 0 |
| cost | $0.00 | $0.00 |
| tokens out | 0 | 0 |
| workdir | `/p/lustre3/haridev/1kg-eval/bare/1kg-20260915_161213` | `/usr/WS2/haridev/dftracer-agents/workspaces/1000genome_workflow/20260915_231313` |

## Traces produced

Event counts are parsed from the files, not taken from any
agent's report. A trace holding only `CM`/`HH`/`FH`/`SH`
records is DFTracer's own header with no application events in
it -- recorded here as such rather than counted as a success.

| arm | file | bytes | events | app events |
|---|---|---|---|---|
| bare | `scratch_test/trace/test-246c3a94fe4b0a7e-app.pfw.gz` | 277 | 10 | end;foo;start;thread_name |
| bare | `source/trace/individuals-bc3234d9cb707aab-app.pfw.gz` | 0 | 0 | **none** |
| phronix | `baseline/traces/compact/baseline-673b180b-d106597a4933fe30-app.pfw.gz` | 880 | 13 | compress;end;main;processing;readfile;start;thread_name |
| phronix | `baseline/traces/raw/baseline-673b180b-d106597a4933fe30-app.pfw.gz` | 880 | 13 | compress;end;main;processing;readfile;start;thread_name |

## Layout

```
bare/, phronix/   raw stream-json, readable log, workdir manifest,
                  per-step and per-phase CSVs
traces/           every non-empty .pfw* both arms wrote, plus
                  trace-inventory.csv with parsed event counts
eval5_phases.csv  the data behind figure 5a
eval5b_quality.csv  the rubric behind figure 5b (hand-scored,
                  each row carrying its evidence)
rendered/         figures and tables built from the above
```
