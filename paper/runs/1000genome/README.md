# eval5 — 1000genome

Collected 2026-09-15 17:56. Everything here was produced by
`paper/figures/eval5_collect.py`; nothing is transcribed by hand.

* application: `https://github.com/pegasus-isi/1000genome-workflow @ master`
* dataset: `/p/lustre3/haridev/1kg-eval/data`
* smoke test: `python3 bin/individuals.py ALL.chr1.tiny.vcf 1 0 300 300`

## Runs

| | bare | phronix |
|---|---|---|
| finished | True | True |
| turns | 51 | 2 |
| cost | $1.11 | $4.12 |
| tokens out | 23,347 | 600 |
| workdir | `/p/lustre3/haridev/1kg-eval/bare/1kg-20260915_165536` | `/usr/WS2/haridev/dftracer-agents/workspaces/1000genome_workflow/20260915_235814` |

## Traces produced

Event counts are parsed from the files, not taken from any
agent's report. A trace holding only `CM`/`HH`/`FH`/`SH`
records is DFTracer's own header with no application events in
it -- recorded here as such rather than counted as a success.

| arm | file | bytes | events | app events |
|---|---|---|---|---|
| bare | `run/trace/individuals-2f1e0190c404c096-app.pfw.gz` | 30,886 | 2512 | compress;end;readfile;start;thread_name;write_individual_file |
| phronix | `tmp/run/trace-f051c67f043b7130-app.pfw.gz` | 30,193 | 2520 | compress;compress_tar;end;processing;readfile;start;thread_name;vcf_read_filter;write_individual |

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
