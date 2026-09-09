# Figures

Each evaluation is a `evalN_extract.py` (runs -> CSV) and a `evalN_plot.py`
(CSV -> PDF). Pass the run directory names to the extractor:

    python eval1_extract.py --runs <run-dir-name> ...
    python eval1_plot.py

    python eval2_extract.py --runs <run-dir-name> ...
    python eval2_plot.py

`figtools.py` holds the axis rules every figure obeys: when a plot carries a
second y-axis, both axes get the SAME number of major ticks, so the two
scales share one set of horizontal rules instead of interleaving at unrelated
heights -- a reader must never be able to mistake a left-axis gridline for a
level on the right-hand scale. The left axis also carries minor ticks; the
right does not, since doubling the marks along that spine adds no precision.

`style.yaml` holds what every figure shares: the 18pt base font, the named
canvas sizes (`wide` 18x4, `column` 8.5x4, `square` 4x4) and the validated
categorical palette. Change it there, not in a script.

## Eval 1 -- `eval1_capabilities`

How many capabilities phronix built per task category, and how many came back.

Categories are the upstream repositories the SWE-bench tasks come from --
the closest thing the benchmark has to a task type.

Each category carries two stacked bars. A stack is total capabilities, split
by colour into skills and MCP tools. The hatch says which run mode the number
comes from -- so colour and hatch each carry one variable, and neither is read
off colour alone.

The two stacks answer different questions and must not be summed. A **fresh** run starts with an empty store, so everything in it was
built during that run; a **reuse** run reads what the fresh runs promoted.
The reuse bar is what makes the other two worth anything: a reuse run creates
almost nothing because the capability it needed already existed.

Left stack, plain: what a fresh run BUILT.

* `skills_created` -- new skill directories, from each task's own record.
* `tools_created` -- MCP tool modules the run promoted, de-duplicated across
  the run. Counted from `promoted`, not from the store on disk, because a
  reuse run's store arrives pre-filled and the directory listing would credit
  it with tools it inherited.
Right stack, hatched: what a reuse run LOADED.

* `skills_reused` -- learned skills retrieved. The framework's own
  `phronix-*` skills are excluded: they load on every task by design, so
  counting them would report the harness working rather than the corpus
  paying off.
* `tools_reused` -- calls to a learned MCP tool, from the trace, charged to
  the task that made the call. A call counts as learned when its name matches
  a tool module the corpus promoted, so the framework's own services never
  need to be listed and cannot go stale.

Fresh runs show zero tool reuse. That is the measurement, not a gap: a fresh
run writes tool modules but does not call them again within the same run.

Tools are filed by subject rather than by the task that wrote them, so a tool
is charged to a category by the repo named in its filename, falling back to
its directory; anything neither names lands in `general`.

### The right-hand axis

The line answers: of the tasks a fresh run SOLVED -- and so left a working
skill for -- how many did the reuse run then solve on its first attempt?

The denominator matters. Scored against every task in the category it folds
in tasks no run ever solved, where there is no successful skill to reuse and a
first-try miss says nothing about determinism. Conditioned properly the rate
is 86% (nano, 12/14), 79% (mini, 11/14) and 67% (gpt-5.4, 14/21); against all
tasks it read 33-53%, which was mostly measuring how hard the tasks were.

Eligibility is checked, not assumed: every fresh-solved task is confirmed to
have a skill directory in that run's store.

A category whose denominator is empty is drawn as a gap, not as 0% -- zero
would assert a failure that was never measured.

It sits on a second axis because it measures TASKS, not capabilities. The two
scales are not comparable by height; read the line only against the
right-hand numbers.

## Eval 2 -- `eval2_tracking`

Automatic tracking and knowledge creation, one bar per model. The stack is
durable knowledge -- skills and MCP tools produced -- and the line is the raw
tracking volume it was distilled from. Read together: a model that tracks
heavily but converts little is doing bookkeeping, not learning.

Fresh and reuse runs are summed per model. Learning is almost entirely the
fresh run's doing (a reuse run finds the capability already written) while
tracking happens in both, so the pair is the model's whole story.

`entries_tracked` is attributed BY TIMESTAMP, not by counting the file. A
reuse run's store arrives carrying the observation log of every run that
promoted before it -- the nano reuse log opens with entries written by the
gpt-5.4 fresh run two hours earlier -- so the file length would credit a run
with tracking it inherited. Only entries at or after the run's own
`created_at` are counted.

`topics` is the number of distinct subjects the tracker filed under. It is in
the CSV but not the figure: it barely moves across models (30-33 everywhere),
which is itself the finding -- the topic vocabulary is set by the pipeline's
stages, not by how much a model learns.
