# Run log — corona (MI50 / gfx906)

Groups of 30 from SWE-bench lite, `nemotron-3.5` (NVIDIA-Nemotron-3.5-Lightning
-30B-A3B, Q4_0) served by llama.cpp on corona. Newest group is appended at the
bottom.

Numbers here are **not comparable to `interesting.md`** — that is Tuolumne, a
different GPU, a different model and a different node shape. Bare-versus-phronix
*within* one corona run is the comparison that holds.

## The shape, and why

| | |
|---|---|
| GPU | 8 × MI50/MI60 (gfx906, Vega20), 32 GB discrete |
| ROCm | 5.7.1 — the only version with gfx906 rocBLAS kernels |
| replica | **2 GPUs** (64 GB), 2–4 slots |
| per node | 4 replicas, `CORES_PER_SERVER=11` of 48 |
| allocation | **5 nodes fleet + 3 nodes agents/containers** |

**Two GPUs per replica, not one.** At one GPU a replica sat at ~30 GB of 32
(94%) and two of sixteen died on the compute buffer at 2 slots. At two GPUs the
same fleet measures 15.8–26.9 GB per card and nothing OOMs.

**The allocation is split, unlike Tuolumne.** Tuolumne co-locates everything: a
4-GPU APU node has 96 cores and the agents mostly wait on the fleet. Corona
cannot — four llama-servers take 44 of 48 cores, and the agents now run on the
compute nodes too, so a co-located node would have four cores for thirty agents.

**Agents run on the compute nodes, not the login node.** They used to run
wherever the harness did, which here is a shared login node: measured at 12
tasks, 60 `claude` processes and load 10.8 on 48 cores while every allocated
compute node sat at 0.00. The allocation was being used for containers and
nothing else, and the ceiling on parallelism was a machine outside it.

## What the hardware actually does

Measured under load, 20 replicas:

| | |
|---|---|
| decode | **26 tok/s per replica**, ~525 tok/s fleet |
| prefill | ~2500 tok/s fleet |
| prompt cache | reuses ~6.6–7.1k of every ~10k-token prompt |

**Per-agent decode is the number that decides whether a task finishes**, and it
is decode ÷ concurrent requests on that replica:

| shape | per agent |
|---|---|
| 12 replicas × 4 slots, 30 tasks | 7 tok/s |
| 20 replicas × 2 slots, 30 tasks | **13.5 tok/s** |

At 7 tok/s a 20-turn attempt cannot finish inside its 1800s budget, and 60
task-arms ran 18 minutes with zero completions — not stuck, each crawling.

The prompt cache is **not** the problem: it is already avoiding most prefill.

## Budgets have to be scaled, and bounded

The stage budgets were calibrated against a local model at ~1000 tok/s. At 13.5
tok/s the same budget buys 1/70th of the work. `budget_scale()` measures this
and reports 50× (clamped) — but it was only ever applied to the *parallel*
research pipeline, not to the tracked loop.

Unscaled, this is what it cost: **178 of one run's 314 pipeline faults were
stages killed at their ceiling.** Research died mid-diagnosis reporting
`no PROBLEM/APPROACH/ANSWER`, so try 2 opened with "no skill covers this task;
solving from scratch" — the research→skill→try2 chain never completed once.

The tracked loop is sequential (research blocks the next attempt, a fold blocks
research), so 50× would put one stage at four hours. It is bounded at **6×**,
derived from tokens rather than seconds: a diagnosis is ~8–15k output tokens,
which is 600–1100s at this rate against a 300s budget.

## Pipeline faults vs model failures

```bash
scripts/error-report.py [<run-dir>]
```

The two read identically in a trace and are worth acting on differently. A
pipeline fault is ours; a model failure is the benchmark working. Anything
unrecognised is reported as UNCLASSIFIED rather than assumed to be a model
failure — a fault the report does not know about is the one worth seeing.

## Faults found on corona, and what each looked like

Each of these read like something else, which is the reason they are written
down:

| looked like | actually was |
|---|---|
| replicas "crashing and coming back" | a 4s probe timeout + one-miss-means-down; **not one server ever restarted** |
| a broken agent (`exited rc=127`) | VS Code updated its extension 2.1.246→2.1.247 mid-run and deleted the path the harness had baked in |
| a broken image (`kex_exchange_identification`) | sshd `MaxStartups`: 30 agents opening connections at once |
| a full disk (`disk quota exceeded`) | the kernel keyring at 200/200 — ~110 containers per node the reaper never cleaned, because it looped over `$(hostname)` and pruned a store resolved on the wrong side |
| a broken agent producing nothing | Lmod exports `module`/`ml` as `BASH_FUNC_module%%`; the remote wrapper exported them, `export` failed, and the shell ran the function bodies as commands — the script was corrupt from that line on |
| the benchmark's own test suite breaking | tasks `pip install -e .`-ing themselves into the harness venv |

**The venv one is worth reading twice.** The tasks *are* Python repositories and
an agent reproducing a bug installs the repo it is working on. Seven SWE-bench
repos were editable-installed into the harness's site-packages; `pytest` was
replaced by a task's 4.6.1 checkout and `pluggy` dragged to 0.13.1. One `.pth`
pointed into the **previous day's run**, so it had been changing what every later
task imported, silently, across runs.

Two softer guards leak and should not be trusted: dropping `VIRTUAL_ENV` and the
venv from PATH is undone by `tool_path_env` (node lives there), and a `pip` shim
earlier on PATH never sees `python -m pip` or the absolute `bin/pip`. Use:

```bash
scripts/seal-venv.sh          # before any long run
scripts/seal-venv.sh --open   # to install into it
```

## Running the list

```bash
scripts/corona-300.sh              # all ten groups of 30 to pbatch
scripts/corona-300.sh 3 7          # groups 3..7
DRY=1 scripts/corona-300.sh        # print, submit nothing
```

Each group is one `flux batch` job that brings up its own fleet, runs its
thirty, and tears down — so a group that dies takes nothing with it, and they
start as the scheduler frees nodes. `-t 7h` is double the 3h30m a group measured.

---
