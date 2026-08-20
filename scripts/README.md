# Running the benchmark

The benchmark asks one question: **does phronix's research and learning make an
agent solve more SWE-bench tasks than the same agent without it?**

Every run is a pair of arms — `<harness>-bare` and `<harness>-phronix` — on the
same tasks, in the same containers, with the same model. The only difference is
phronix. Both arms run concurrently; tasks within an arm stay in a fixed order,
because the learning arm's task N is supposed to benefit from tasks 1..N-1 and
that only means something if every arm saw the same sequence.

Scripts live here, in the repository, so they are versioned. **Data never does**
— run directories, container images and the dataset live on the PFS at
`/p/lustre5/haridev/phronix-bench`, which is where the space is.

## Quick start

```bash
scripts/run-benchmark.sh                     # claude, 6 tasks, fresh
scripts/status.sh                            # watch it (newest run, in detail)
scripts/running.sh                           # what is it costing right now
scripts/kill.sh                              # stop everything
```

Measure the cost on one task before committing to six:

```bash
scripts/run-benchmark.sh --tasks pilot-1.txt
```

## The scripts

| script | what it is for |
| --- | --- |
| `run-benchmark.sh` | Launch a run. Stops any previous one first |
| `status.sh` | The newest run, in detail. `--all` for every run, `--list N` for names, or a run name |
| `running.sh` | Is anything spending money right now, and what has it cost |
| `kill.sh` | Stop every benchmark process, on this node and others. `--dry-run` previews |
| `launch-when-ready.sh` | Wait for the model endpoint to accept requests, then launch |

## Check the environment before spending anything

```bash
scripts/baseline-check.sh                       # all 9 tasks, unpatched
scripts/baseline-check.sh --tasks fast-6.txt --node tuolumne1075
```

Runs every task's tests with **no patch and no agent** — one container each, no
tokens — and answers the question a run cannot: *can this instance be judged at
all?* Three faults it catches, all measured here:

* **no runner in the image.** sympy's testbed env ships without pytest, so every
  test scored not-passed. The verdict was indistinguishable from a
  catastrophically wrong patch, three retries were spent on it, and the baseline
  cached 30 tests as already broken. pytest is now installed into the
  *container* when missing — never the host venv, because the instance pins the
  dependency versions its tests are written against.
* **ids that cannot match.** SWE-bench stores sympy's ids as bare function
  names; pytest prints full node ids. Every sympy instance scored 0 of 30 on
  tests that had just printed PASSED.
* **fixtures handed to pytest as tests.** flask-4992's test patch adds
  `tests/static/config.toml`; pytest given a data file collects nothing at all.

A run that cannot execute its tests produces numbers that look like results, so
this is cheap insurance. Exit status is non-zero when any instance is unusable.

## Options that change what is measured

`run-benchmark.sh` takes these; the rest are in `--help`.

**`--harness claude|opencode`** — which agent runs the tasks. Both drive the
same phronix, so a phronix result means the same thing either way. Numbers are
**not** comparable *across* harnesses: different system prompt, different model
routing. Bare-versus-phronix *within* one run is the comparison that holds, and
it is the one the benchmark is for.

**`--fresh` (default) / `--reuse`** — `--fresh` ignores skills and research from
earlier runs and starts from the bundled framework alone. That is what makes a
result an evaluation of the approach rather than of an accumulated store. What a
fresh run finds is still synced back afterwards, so nothing is wasted.
`--reuse` is the system working as intended — research is expensive and the
point of keeping it is not paying twice — but a reusing run cannot answer "does
this approach work from scratch".

**`--research-on-retry`** — withhold research from the first attempt, so it runs
only after that attempt has failed. Try 1 is then the same first move the
baseline makes, and what gets measured is what research *recovers* rather than
what it adds up front. A narrower claim, and an easier one to defend.

**`--tries N`** — the ceiling. Retries stop early anyway when two consecutive
attempts repeat a patch, because a task that cannot change its answer is only
spending tokens.

## Reading the result

`status.sh` prints one line per task:

```text
PASS  pylint-dev__pylint-7080   steps=43 tok= 106,461 time=133s  research tok=104,239 time=963s
      research: survey 80s | plan 133s | aspect 3x max 404s !1cut | collect 72s | ...
```

Task tokens and time are separate from research tokens and time, because a first
attempt looks expensive when research runs and one combined number cannot say
whether that was the agent working on the task or the framework working out how
to. `tries=` appears only when it actually retried. Parallel stages report
**max**, not sum — three concurrent aspects cost the task their slowest member,
and summing them overstates research against solve on every line. `!Ncut` marks
stages that hit their budget: those findings are partial and were paid for in
full.

## Stopping safely

`kill.sh` never matches on the binary name. An interactive Claude Code session
uses the same `claude` executable the benchmark spawns, so `pkill -f claude`
would kill the session issuing the kill. Agents are matched on the **benchmark
run path**, which appears in every spawned agent's argv and in nothing else.

It also reads `logs/`, where `run-benchmark.sh` records the pid and host of
every run it starts. The process table is node-local — a run launched on the
login node is invisible from a compute node, so `pgrep` reports "not running"
for a runaway that is still spending. The record survives the allocation.

Finally it verifies rather than assumes: a kill that silently failed is worse
than no kill at all, because it reads as "stopped" while the account keeps being
charged.

## When a run produces nothing

Attempts reporting `0 steps, 0 tok` almost always mean the agent never started,
not that it ran and did nothing. Two causes have actually occurred:

* **The model endpoint refused every request.** The shared LiVAI key hit its
  spend cap and returned 429 to everything. `preflight` now checks the endpoint
  before a run starts and prints the provider's own message.
* **A phronix research pass never ran.** That is fatal and stops the run: an arm
  whose research never starts degrades into a plain agent with extra
  scaffolding, and every number it produces would be attributed to phronix.
