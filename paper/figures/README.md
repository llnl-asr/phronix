# Figures

Regenerate everything from the runs:

    python extract_capabilities.py --runs <run-dir-name> ...   # -> .csv
    python plot_capabilities.py                                # -> .pdf

`style.yaml` holds what every figure shares: the 18pt base font, the named
canvas sizes (`wide` 18x4, `column` 8.5x4, `square` 4x4) and the validated
categorical palette. Change it there, not in a script.

## capabilities_by_category

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

`resolved_first_try` counts tasks a reuse run solved on its first attempt with
no retry -- the determinism claim: the corpus told the run what to do rather
than it searching for the answer again. Aggregated over the three models it
roughly doubles from fresh to reuse (7->16 nano, 6->14 mini, 8->14 gpt-5.4).

It sits on a second axis because it counts TASKS, not capabilities. The two
scales are not comparable by height and the line is not a series in the
stacks; read it only against the right-hand numbers.
