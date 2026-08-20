# phronix benchmark — does self-learning actually help?

A controlled comparison on SWE-bench, measuring **tries**, **tokens consumed**, and
**learning rate**: whether an agent that accumulates skills gets measurably better
at later tasks than one that does not.

Everything here holds the model fixed at **`livai/claude-sonnet-4.5`** so the only
variable is the scaffolding.

---

## The claim under test

phronix's thesis is that a session which records what it learned makes the *next*
session cheaper and more likely to succeed. That is a falsifiable claim, and this
benchmark is the corrector for it — the same discipline the framework applies to
its own skills, applied to the framework itself.

If the claim is true, the phronix arm's resolve rate should **rise** across the
run while the others stay flat, and its tokens and tries per task should **fall**.

If it is false, this benchmark is how we find out. That is the point of building
it, and a run that shows no learning is a real result, not a failed experiment.

---

## Arms

| Arm | Scaffolding | Learning | What it isolates |
|---|---|---|---|
| `mini` | mini-swe-agent's own agent | none | the published reference point |
| `opencode-bare` | opencode, no phronix | none | the harness on its own |
| `opencode-phronix-frozen` | opencode + phronix, store **read-only** | none | **the control** — phronix's scaffolding without learning |
| `opencode-phronix` | opencode + phronix, store read-write | accumulates | the full claim |

### Why four arms, when three were asked for

The fourth arm is the one that makes the result mean anything.

phronix changes two things at once: it adds scaffolding (retrieval tools, agents,
standing rules) *and* it learns. With only `bare` vs `phronix`, a rising resolve
rate cannot be attributed to learning — it could be the scaffolding helping
uniformly while the apparent "improvement" is just easier tasks landing later in
the fixed order.

`opencode-phronix-frozen` runs the identical scaffolding with the skill store
mounted read-only. Any *slope difference* between frozen and full is attributable
to learning specifically, because that is the only thing that differs.

`--arms` selects which to run; the frozen arm can be skipped for a quick look,
but a learning-rate number reported without it is not evidence.

---

## Metrics

### Per task

| Metric | Definition |
|---|---|
| `resolved` | the instance's official `FAIL_TO_PASS` / `PASS_TO_PASS` tests pass |
| `tries` | independent attempts, from a clean container, until resolved (cap `--max-tries`) |
| `steps` | agent turns within an attempt |
| `tokens_*` | input / output / cache, from the harness's own telemetry |
| `cost_usd` | as reported by the provider |
| `skills_created` | skills or lessons written during the task |
| `skills_reused` | skills retrieved that were written by an **earlier task** |
| `wall_s` | wall-clock, including container setup |

Both senses of "tries" are recorded: attempts-to-pass (the headline, which should
fall as skills accumulate) and steps-per-attempt (which measures verbosity, and
is already in the telemetry).

### Across the run — the learning rate

```text
learning_rate:
  resolve_slope   +0.021 / task      # OLS slope of resolved(0/1) vs task index
  reuse_rate       0.43              # tasks citing a skill from an earlier task
  tokens_slope    -1,840 / task
  tries_slope     -0.08 / task
```

`resolve_slope` says performance improved. `reuse_rate` says *learning* is why —
without it, a positive slope is indistinguishable from task-ordering luck. Both
are reported for every arm; for the no-learning arms `reuse_rate` is 0 by
construction and their `resolve_slope` is the null distribution the phronix arm
must beat.

A rolling-window curve accompanies the scalars, because a slope fitted to 30
noisy binary outcomes has a wide confidence interval and should never be quoted
alone. The report prints the CI.

---

## Isolation

Repeatability is the whole basis of the comparison, so:

- **One podman container per attempt**, from the official SWE-bench image for that
  instance. Rootless, which is the right fit for a shared login node where the
  Docker daemon is often restricted.
- **A fresh container per try.** A retry that inherits the previous attempt's
  filesystem is not an independent attempt.
- **Fixed task order**, pinned in `tasks/*.txt` and shared by every arm. Order
  matters enormously for the learning arm; varying it between arms would make the
  comparison meaningless.
- **A fresh skill store per run**, seeded from the bundled framework skeleton only
  — `--fresh` guarantees no skill from a previous run leaks in.
- **The store is snapshotted after every task**, so a run can be audited or
  replayed and you can see exactly which skill existed when.
- **Model pinned** to `livai/claude-sonnet-4.5` for every arm.

What is deliberately *not* isolated: the skill store persists **across tasks
within a run** for the learning arm. That carry-over is the effect being
measured.

---

## Threats to validity

Stated because a benchmark that hides these is worse than none.

1. **Training-data contamination.** SWE-bench instances predate the model and may
   be memorised. This inflates every arm equally, so *differences* remain
   meaningful while *absolute* resolve rates do not.
2. **Order effects.** With one fixed order, a positive slope could be easy tasks
   landing late. Mitigated by the frozen control (same order, no learning) and by
   `--seeds` for multiple orderings when budget allows.
3. **Skill overfitting.** A skill written for one repo may be useless elsewhere.
   `reuse_rate` counts cross-task reuse; `reuse_rate_cross_repo` is reported
   separately, and it is the harder and more meaningful number.
4. **Token asymmetry.** The phronix arm carries more tool schemas, so its
   *per-step* token count starts higher. The comparison that matters is
   tokens-per-*resolved-task*, which is what the report leads with.
5. **Small N.** 30 tasks gives wide intervals. The default is chosen for
   affordability, not for statistical power; treat a single 30-task run as a
   signal to invest in a larger one, not as a conclusion.

---

## Running it

The benchmark lives in `tests/` and is a development tool, not part of the
installed package — so it is invoked as a module from a checkout, not as a
console script:

```bash
cd <phronix checkout>
export BENCH="python -m tests.benchmark.cli"

# One-time: pin a task list and cache the dataset locally (needs network once)
$BENCH tasks --split lite --limit 30 --seed 0 \
    --dataset-cache tests/benchmark/.dataset \
    --out tests/benchmark/tasks/lite-30.txt

# A full comparison, fresh store, no leakage from previous runs
$BENCH run --tasks tests/benchmark/tasks/lite-30.txt \
    --dataset-cache tests/benchmark/.dataset \
    --arms mini,opencode-bare,opencode-phronix-frozen,opencode-phronix \
    --max-tries 3 --out tests/benchmark/runs/$(date +%Y%m%d-%H%M)

$BENCH report tests/benchmark/runs/<id>          # tables + learning curve
$BENCH report tests/benchmark/runs/<id> --json   # machine-readable
```

`--fresh` is the default; pass `--no-fresh` only if you deliberately want a run
to inherit a previous run's skills, which breaks from-scratch comparability.

### Prerequisites

- `opencode` on PATH, with the `livai` provider configured and `OPENAI_API_KEY` set
- `podman` (or `--isolation docker`)
- `mini-swe-agent` installed, for the `mini` arm only

> **Note on installing mini-swe-agent here:** this machine's `~/.pip/pip.conf`
> (written by NVIDIA PyIndex) adds `https://pypi.ngc.nvidia.com` as an extra
> index, which does not resolve on this network — every package burns five
> retries against it. `pypi.org` itself works. Install with the extra index
> suppressed for that command only:
>
> ```bash
> PIP_EXTRA_INDEX_URL= pip install mini-swe-agent
> ```
