# Figures

Each evaluation is a `evalN_extract.py` (runs -> CSV) and a `evalN_plot.py`
(CSV -> PDF). Pass the run directory names to the extractor:

    python eval1_extract.py --runs <run-dir-name> ...
    python eval1_plot.py

    python eval2_extract.py --runs <run-dir-name> ...
    python eval2_plot.py

    python eval3_extract.py --runs <run-dir-name> ...
    python eval3_plot.py

    python eval4_extract.py --runs <run-dir-name> ...
    python eval4_plot.py

## Models, panels and repeats

The paper reports three models -- `gpt-5.4`, `gpt-5.5`, `gpt-5.6-sol` -- named
once in `figtools.MODELS` and read from there by every plotter.

**Evals 1, 3 and 4 emit one figure per model**, lettered by position:
`eval1_capabilitiesa.pdf` is 5.4, `...b.pdf` is 5.5, `...c.pdf` is 5.6-sol.
A letter rather than the model name, because the prose cites "figure 1b" and a
model rename must not invalidate the reference. They were one figure with a
panel per model, which forced all three to share a y scale: the model with the
largest corpus set the axis and the other two were read off the bottom fifth
of it.

**Eval 2 stays a single figure**, models along the x axis -- that comparison is
the figure's subject rather than a way of splitting it.

### Variance

Every value is a mean over repeated runs, drawn with the spread across those
runs, so a difference between two bars can be read against how much either
wanders on its own. The CSVs therefore carry a `run` column and one row per
run; nothing is summed at extract time.

* The error bar is the SAMPLE standard deviation (n-1) across runs.
* It sits on the TOTAL of a stacked bar, never on each segment -- the segments
  are parts of one measured height, and intervals up the side of one column
  cannot be added by eye. Where two segments are counted separately per run,
  their spreads add in quadrature.
* **A single run gets no error bar at all**, rather than one of zero length. A
  zero-length bar asserts perfect stability, which is the opposite of what one
  run measures. Every figure carries `n=` in its lower right so the two cases
  are never confused.

**Repeats are grouped within a condition before conditions are combined**, and
the ordering matters. A model contributes a fresh run and a reuse run; treating
those as two repeats reports the fresh-versus-reuse difference -- the largest
signal in the sweep -- as though it were noise. So eval 2 and eval 3 average
repeats within each mode first and combine the modes afterwards. Eval 4 needs
no such care: its `group` column already separates the arms. Eval 1 keys on
mode directly.

One case looks like a mistake and is not: the **bare** arm shows n=2 with a
single fresh/reuse pair, because a bare arm runs in both and phronix's
knowledge policy means nothing to it. Those two really are repeats of one
condition, and the spread they show is real.

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


## Eval 3 -- `eval3_retries`

RL-driven research, priced in attempts. Cost is drawn as LINES on the left
axis and knowledge as a stacked BAR on the right: four bars in a row read as
one series of four, and the distinction between "what it cost" and "what it
produced" should be structural rather than something the reader carries over
from the legend.

A category with no task of a given outcome draws a gap, not a zero -- astropy
solved nothing across all three models, and a zero there would claim it solved
something in zero attempts.

**The bare column is an estimate, not a measurement.** Bare has no retry loop
-- every bare task runs exactly once and is scored -- so its budget is assumed
to be `--bare-retries` (default 5) attempts, priced from the one attempt that
actually ran. It is drawn hatched for that reason, and no conclusion should
rest on its exact height. Change the assumption with the flag; the CSV records
what was used.

**Phronix is split by outcome because the two halves say opposite things.** A
solved task's attempt count is what the research SAVED: 1.1-1.7 attempts
across every category. A failed task's is just the budget cap being spent
(2.9-3.6), and reading the two together as one average would hide both.

Topics are de-duplicated across the sweep: a run that revisits a topic has not
learnt a second one.

Research itself writes no tool modules -- it emits a plan and a skill, and the
capability builder turns those into tools -- so the MCP half of the stack is
counted from the capability tree, not from `research/`.


## Eval 4 -- `eval4_tokens`

Token cost of a TASK, three arms per category, each split by outcome.

* **Bare (x5 est.)** -- every bare task, scaled by `--extrapolate` (default 5).
* **Phronix, fresh** -- every phronix task in a fresh run.
* **Phronix, reuse** -- reuse applying what was successfully learnt: tasks
  whose own model solved them in the fresh run (leaving a skill, confirmed on
  disk) and which the reuse run then solved on its FIRST attempt. By
  construction there are no failures here; a retry would mean the corpus had
  not supplied the answer, which is a different thing to measure.

**Per task, and bare scaled.** Per ATTEMPT, bare looks cheap for a reason that
flatters it: it takes exactly one attempt and stops, win or lose. Measured
that way bare came out at 334K against reuse's 828K, which says only that
phronix carries more context per turn. Against the retry budget the comparison
actually assumes, the order reverses: 1.67M for bare, 797K for reuse. The x5
is an assumption, not a measurement -- it is the figure's main soft spot, and
it is recorded per row in `bare_multiplier`.

**Watch the token unit.** 88-92% of these counts are prompt-cache reads, which
are billed at a fraction of fresh input. Phronix carries a large skill context
that is re-read every turn, so raw token totals overstate its cost relative to
dollars. The CSV keeps the totals; a cost-based version would favour phronix
further.

The two segments sum correctly: both are divided by the group's TASK count, so
they stack to its overall tokens-per-task. Categories are ranked by the work
the fresh arms did -- the reuse group is a filtered subset, and letting it vote
would rank categories by how much reuse succeeded.

Colour carries the outcome and texture the arm, so neither is read off colour
alone. Green and red are the reserved status steps, because success and
failure genuinely are a status, and both carry a written label.


## Eval 5 -- `eval5_session`

One agentic pipeline session, measured, against a bare control.

    # phronix arm: the interactive session you ran (or a headless log)
    python eval5_extract.py --latest 1
    python eval5_extract.py \
        --phronix ~/.claude/projects/<slug>/<uuid>.jsonl \
        --bare    ~/.claude/projects/<slug>/<other>.jsonl

Both transcript shapes work: interactive sessions under
`~/.claude/projects/<slug>/`, and headless `--output-format stream-json` logs.
They carry the same records; the interactive one adds the human turns, which
is the point of measuring it.

**`human_turns` counts what the person actually typed** -- detected by
`origin.kind == "human"`. Every other `user` record is a tool result being fed
back, and counting those reports hundreds of "interactions" for a run nobody
touched.

**`repeats` is the retry signal.** The pipeline keeps no retry counter, so a
step that cannot get past itself is only visible as the same tool called with
the same arguments again. A call repeated with DIFFERENT arguments is
progress and is not counted.

**A step begun and never ended counts as failed** -- a collapsing step does
not report its own collapse.

The bare arm is `scripts/pecan-bare.sh` in the dftracer-agents repo: same
task, same model, same gateway, but run from a scratch directory so the
project's `.claude/` -- agents, skills, hooks, both MCP servers -- is out of
scope. Sharing the project directory would hand the "bare" arm the pipeline's
skills and make the comparison meaningless.


### By phase -- `eval5_pipeline`

    python eval5_steps.py <headless-run>.jsonl     # -> eval5_steps.csv
                                                   #    eval5_phases.csv
    python eval5_plot.py                           # -> rendered/eval5_pipeline.pdf

`eval5_extract.py` answers what the session cost in total; this answers where
the effort went. A phase that succeeded on its first call and a phase that
needed twelve retries both end in success, and only the second is evidence of
anything.

**Four phases, not the pipeline's own steps.** `setup`, `annotate`, `build`,
`smoke` -- the things a bare run also does, so the bare arm can be laid
alongside without inventing steps it never had. `annotate` takes validation
and the init/fini fix with it: both exist only because annotation happened,
and splitting them would credit annotation with less work than it caused.
`eval5_steps.csv` keeps the per-step detail behind the rollup.

**Read the headless stream, not the session transcript.** The orchestrator's
transcript under `~/.claude/projects/` holds only its own 170 calls -- the
annotation and validation subagents write no sidechain records there, so their
216 calls are invisible. The stream-json log has all 405. Measuring the
transcript undercounts the run by more than half.

**Failures belong to the phase that made the CALL**, not the phase open when
the result came back: an annotation subagent's failure is annotation's.

**Colour is the outcome, hatching is the kind.** Green succeeded and red
failed -- the reserved status steps every other figure here uses, so success
and failure read the same way across the paper. Skills and MCP tools are told
apart by texture within the stack, which leaves the status colours one job.

**Four bars per phase: two arms, each split success and failed.** The bare
baseline is a placeholder emitted by `--empty-arm` until that run exists; its
bars are empty by construction, not by measurement.

**The smoke test has calls but no tokens.** It runs inside the build step, so
its capability calls can be separated by tool name and its tokens cannot. The
token lines break at `smoke` rather than dropping to zero -- a gap says "not
measured here", a zero would claim the smoke test was free.

**The token axis is logarithmic, and input includes cache reads.** Input runs
four orders of magnitude above output -- 28-40M against 1-3K per phase -- so a
linear axis would lay the output line flat on zero and read as missing data.
Counting only `input_tokens` is worse: it reports 280 tokens for a phase that
consumed tens of millions, because 88-92% of this run is cache reads. Those
are context the model was actually sent, cheaper per token but not absent, so
they count here; the dollar view belongs in `cost_usd`.

The shape is the result. The failures and all 11 tool repairs sit in `setup`
and `build`; `annotate` is the largest phase by far and never failed once,
running on skills that already knew the job. The failures are the self-healing,
and they stop once the tool is fixed.
