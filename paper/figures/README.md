# Figures

Regenerate everything from the runs:

    python extract_capabilities.py --runs <run-dir-name> ...   # -> .csv
    python plot_capabilities.py --sizes wide column square     # -> .pdf

`style.yaml` holds what every figure shares: the 18pt base font, the named
canvas sizes (`wide` 18x4, `column` 8.5x4, `square` 4x4) and the validated
categorical palette. Change it there, not in a script.

## capabilities_by_category

How many capabilities phronix built per task category, and how many came back.

Categories are the upstream repositories the SWE-bench tasks come from --
the closest thing the benchmark has to a task type.

The three series are counted from two different run modes and must not be
summed. A **fresh** run starts with an empty store, so everything in it was
built during that run; a **reuse** run reads what the fresh runs promoted.
The reuse bar is what makes the other two worth anything: a reuse run creates
almost nothing because the capability it needed already existed.

* `skills_created` -- new skill directories, from each task's own record.
* `tools_created` -- MCP tool modules the run promoted, de-duplicated across
  the run. Counted from `promoted`, not from the store on disk, because a
  reuse run's store arrives pre-filled and the directory listing would credit
  it with tools it inherited.
* `skills_reused` -- capabilities loaded from earlier learning.

Tools are filed by subject rather than by the task that wrote them, so a tool
is charged to a category by the repo named in its filename, falling back to
its directory; anything neither names lands in `general`.
