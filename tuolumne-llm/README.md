# llama.cpp inference cluster on Tuolumne (MI300A)

Scripts live here in the repo; everything large — the llama.cpp clone, the venv,
the GGUF models, logs — lives on `/p/lustre5/haridev/llm-tuolumne`.

One `llama-server` per MI300A GPU (4 per node), all serving the **same** model, with
a LiteLLM gateway on a compute node load-balancing across every replica.

## Quick start

```bash
tuolumne-llm/setup.sh                                   # once: venv, clone, models
flux proxy <alloc-jobid> tuolumne-llm/build.sh          # once: ROCm/gfx942 build

flux proxy <alloc-jobid> tuolumne-llm/deploy.sh         # START: stage + launch
tuolumne-llm/status.sh                                  # live view (a = all replicas, q = quit)
flux proxy <alloc-jobid> tuolumne-llm/stop.sh           # STOP: tear down + reap
```

### Getting an allocation

Everything below runs INSIDE a Flux allocation, and `flux proxy <alloc>` is how a
command reaches it. Nothing works without one:

```bash
# ask for one — 8 nodes for 12 hours
flux alloc -N8 -t 12h --queue=pbatch

# or submit and let it start when the scheduler is ready
flux batch -N8 -t 12h --queue=pbatch --wrap "sleep infinity"

# what you have, and whether it is usable yet
flux jobs -a
```

The state column is what matters. **`R` is running and can host work**; `S` is
scheduled and has not started; `TO` has timed out. A `flux proxy` against
anything but `R` fails with *"Unable to resolve &lt;id&gt; to a URI"*, which reads
like a typo rather than an expired reservation — measured the hard way, with a
benchmark that lost its fleet and its container hosts mid-run when the
allocation hit its wall.

Check the time remaining before starting anything long:

```bash
flux jobs -a --no-header | awk '$5=="R"{print $1, $6" nodes", $8" left"}'
```

### Starting the cluster

`deploy.sh` is the one command. It stages the weights onto every node's local
SSD, launches one server per GPU **in parallel**, starts the gateway, waits for
health, and writes `cluster.json` — which is the only thing the benchmark needs
to find the fleet.

```bash
# gpt-oss-120b on every GPU (the default): 32 replicas of one model
flux proxy <alloc> tuolumne-llm/deploy.sh

# a different model everywhere
flux proxy <alloc> tuolumne-llm/deploy.sh nemosuper

# a MIXTURE: one model per GPU, repeated on every node
flux proxy <alloc> tuolumne-llm/deploy.sh gptoss120 nemosuper gptoss20 nemotron

# greedy sampling, for a run whose point is reproducibility
SAMPLING=greedy flux proxy <alloc> tuolumne-llm/deploy.sh
```

Model keys: `gptoss120`, `gptoss20`, `nemosuper`, `nemotron`, `muse`, `ornith`.

**Serving on part of an allocation.** `NNODES` makes the fleet take a PREFIX of
the allocation and leave the rest free — which is what you want when the same
allocation also has to run the benchmark's evaluation containers, because a node
serving four llama-servers has no room for them and a container competing with a
server slows the model for every task.

```bash
# 16-node allocation: fleet on the first 8, benchmark on the other 8
NNODES=8 flux proxy <alloc> tuolumne-llm/deploy.sh gptoss120
```

Do not assume the fleet got the nodes it asked for. Asked for 8 nodes this
deploy landed 23 servers on 6 — two nodes never came up at all. `deploy.sh` now
rebuilds the gateway config from the per-GPU records each replica writes as it
starts, so the gateway advertises what exists rather than what was intended, and
`scripts/run-group.sh` derives its container hosts the same way — the allocation
minus whatever is actually serving, minus anything that refuses ssh.

```bash
tuolumne-llm/status.sh          # replicas up, and on which hosts
```

### Redeploying

Stop first, then deploy. `deploy.sh` does not tear down what is already there,
and two fleets on one allocation fight over ports and GPUs:

```bash
flux proxy <alloc> tuolumne-llm/stop.sh
NNODES=8 flux proxy <alloc> tuolumne-llm/deploy.sh gptoss120
```

`stop.sh` cancels every `llama-*` and `litellm-*` job and reaps orphaned servers
on every node. One thing it cannot reach: a gateway started BY HAND rather than
through Flux — `flux cancel` only knows about jobs. If you have restarted one
manually, kill the process too, or it keeps serving a stale config from the old
run directory on the same port.

Re-deploying costs almost nothing when the weights are already on the nodes:
staging is skipped per node when the copy is there, so only the servers restart.

**Staging is why it is fast and reliable.** Every server otherwise reads its
weights off lustre, and gpt-oss-120b is 63 GB — eight nodes starting together
ask the PFS for half a terabyte at once and it does not share it evenly.
Measured on an unstaged launch: 20 of 32 servers healthy at five minutes, three
whole nodes still short of ready at fourteen. `deploy.sh` copies each model to
`/l/ssd` with `dcp` first, skips nodes that already have it, and then every
server loads locally.

| var | default | meaning |
|---|---|---|
| `PROFILE` | `agent` | tuning profile, see below |
| `SAMPLING` | `diverse` | `diverse` (temp 0.7) \| `greedy` (temp 0, argmax) |
| `MODEL_CACHE` | `/l/ssd/$USER/models` | where staged weights live — **not** `/tmp`, which is tmpfs here |
| `SKIP_STAGE` | unset | assume the weights are already local |
| `PPN` | 64 | `dcp` ranks per node |
| `GPTOSS_EFFORT` | `high` | gpt-oss reasoning effort |

### Stopping the cluster

```bash
flux proxy <alloc-jobid> tuolumne-llm/stop.sh
```

Cancels the jobs and reaps orphaned servers on every node. It reaps by pidfile,
so a server started outside these scripts survives it — if `status.sh` still
shows replicas after a stop, they are almost certainly zombies (`stat=Zl`,
`rss=0`) whose parent has not collected them. Those hold no memory and can be
ignored; a real leftover holds tens of GB and shows in `free -g`.

Environment knobs for `run-cluster.sh`:

| var | default | meaning |
|---|---|---|
| `MODEL` | `nemotron` | `nemotron` \| `muse` \| `ornith` — one model on every GPU |
| `PROFILE` | `balanced` | tuning profile, see below |
| `NNODES` | all | bring up a subset of the allocation (staged rollout) |
| `GPUS_PER_NODE` | 4 | GPUs used per node |
| `GATEWAY_PORT` | 4000 | LiteLLM port |
| `GATEWAY_HOST` | first spare node | where the gateway runs |
| `LLAMA_CTX` | per profile | override the context window |

## Files

| file | role |
|---|---|
| `env.sh` | paths: ROCm 7.2.1, cmake, lustre root, model files |
| `setup.sh` | venv + llama.cpp clone + GGUF downloads (Q8_0) |
| `build.sh` | HIP build for `gfx942` into `build-mi300a` |
| `profiles.sh` | the four tuning profiles |
| `run-cluster.sh` | submits one Flux job per GPU + the gateway, writes `cluster.json` |
| `gpu-server.sh` | one `llama-server` on the GPU Flux bound to the job |
| `gateway-node.sh` | LiteLLM proxy, run as a Flux job on a compute node |
| `status.sh` | top-like live view: throughput, load, and balance (`a` = all replicas, `q` = quit) |
| `session.sh` | what the fleet did over a named window — tokens, prompt-cache reuse, utilisation, balance |
| `bench.sh` | concurrency load generator, aggregate tok/s |
| `stop.sh` | cancels the jobs, then reaps orphans on every node |
| `reap-node.sh` | per-node reaper, by pidfile and by exact executable |
| `cluster.json` | **the running fleet**: gateway, and every replica's host/gpu/port/pid |

`cluster.json` is rewritten on every launch and is what `status.sh` reads by
default, so the project always has a handle on the live fleet:

```json
{ "model": "nemotron", "alias": "nemotron-3.5", "profile": "balanced",
  "gateway": {"host": "tuolumne1171", "port": 4000, "job": "...", "key": "sk-tuolumne"},
  "servers": [ {"host": "...", "gpu": 0, "port": 8050, "pid": 3270626, "pidfile": "..."} ] }
```

## Measuring a window: sessions

Every llama-server counter is cumulative since that server booted, so the live
view can only say *what is happening now* and *what has happened since the fleet
came up*. Neither is what a benchmark asks, which is **what did the fleet do
while my run was going** — and the fleet is up before the run starts and stays up
after it ends.

```bash
tuolumne-llm/session.sh start bench-0822      # mark now; start sampling
tuolumne-llm/session.sh report                # the window so far, without closing it
tuolumne-llm/session.sh stop                  # close it and print the report
tuolumne-llm/session.sh list                  # sessions on disk, newest first
```

Sessions live in `$LLM_ROOT/logs/sessions/<name>/`; the open one is
`sessions/current`, which is why `start` and `stop` take no arguments in a script
that brackets itself. While a session is open, `status.sh` prints it above the
live figures, so one display answers all three questions.

```
session bench-claude-0822-083912  [OPEN]  gpt-oss-120b  profile solo
  window       1m35s  (08:43:13 -> 08:44:48)  8/8 replica(s) up
  tokens       prompt   185.0k   generated    27.9k   total   213.0k
  fleet rate   prompt     1947 tok/s   generated      294 tok/s   (over the whole window)
  when busy    prefill     1924 tok/s   decode      122 tok/s   (prefill 12.7% of fleet-seconds, decode 30.2%)
  prompt cache  96.9% of prompt tokens reused   (2.4M of 2.5M over 46 sampled request(s))
  concurrency  mean   4.1 in flight   peak   5   deferred peak   8   fleet busy 100% of 16 sample(s)
  utilisation   51.6% of 8 replica-slot(s) occupied on average
  balance      0.595 Jain over 8 replicas (lopsided)
```

Two kinds of number, and the report keeps them apart because they are not
equally trustworthy:

* **Counters are differenced** — tokens, prefill and decode seconds, decode
  iterations. End minus start, exact. A replica that restarted mid-session resets
  its counters, so its delta would go negative; those are counted as restarts,
  charged their post-restart total, and named in the header rather than silently
  clamped.
* **Gauges and the prompt cache are sampled** every 5s (`SESSION_INTERVAL`).
  llama.cpp publishes no cache counter at all — the figure comes from `/slots`,
  where each busy slot reports `n_prompt_tokens_cache` for the request it is
  serving — so the hit rate is over *requests observed*, and a request that
  starts and finishes between two samples is invisible. A good estimate on a
  large sample, not an audit.

**Fleet rate versus when-busy** is the pair worth reading together: the first
divides by the whole window, the second by the seconds the GPUs actually spent
prefilling or decoding. Reporting only one makes an idle fleet look slow, or a
slow one look idle. `utilisation` is against replica *slots*, so on the `solo`
profile (one slot per GPU) 8 in flight across 8 replicas is full, not merely busy.

## Watching the cluster

`status.sh` defaults to a live, aggregated, top-style view — one row per node, GPUs
as a four-cell sparkline — refreshing every 2s. Press **`a`** to expand to one row
per replica and again to collapse, **`q`** to quit.

```
nemotron-3.5  profile balanced  gateway tuolumne1171:4000 [UP]  replicas 32/32  live, last 6.0s
  throughput   prompt     9073 tok/s  generate     5516 tok/s  total    14589 tok/s   (counted as requests complete)
  activity         1550 decode iters/s      387.0 slots busy across the fleet
  load           46 in flight      0 deferred   19/32 replicas active
  balance      work 0.994 (balanced)   requests 0.998 (balanced)   (share of decode work)
  lifetime     5.6M tokens  (2.5M prompt + 3.1M generated)

NODE            UP  RUN  DEF    PP t/s    TG t/s    DEC/s   SHARE  GPU4   BALANCE
tuolumne1171    4/4   16    0      1774       424      241   15.6%  [███ ] ██████████
```

Reading it:

- **throughput** — token rates from llama.cpp's counters, which only advance when a
  request *completes*. During long generations they lag, then catch up in bursts.
- **activity** — decode iterations per second and busy slots: the live "is the GPU
  working right now" signal. Iterations are not tokens (one iteration decodes every
  busy slot), so they are never shown as a token rate.
- **balance** — Jain's fairness index over per-replica decode work and in-flight
  requests: `1.000` is perfectly even, `1/32` means one replica is doing everything.
  Above 0.95 reads *balanced*. The line self-suppresses when the queue is draining,
  since a handful of in-flight requests cannot be spread evenly by definition.
- **SHARE / BALANCE** — each node's fraction of fleet work, and a bar relative to an
  even split; the `[████]` cell shows the same per GPU within the node.

Flags: `--once` (single snapshot), `--per-gpu` (start expanded), `--interval N`.

## Tuning profiles

All profiles use Q8_0 weights and greedy decoding (`--temp 0 --top-k 1`, fixed seed,
no penalties), so runs are deterministic and comparable.

| profile | slots/replica | context/replica | KV cache | intent |
|---|---|---|---|---|
| `balanced` **(default)** | 16 | 512k | K turbo4 / V turbo3 | recommended: best measured throughput *and* a large window |
| `throughput` | 32 | 256k | K turbo4 / V turbo2 | most slots, smallest window |
| `context` | 8 | 2.048M | K turbo4 / V turbo2 | maximum token space (8 × 256k slots) |
| `accuracy` | 8 | 128k | f16 / f16 | lossless KV, no prompt-cache reuse |

### Measured (8 nodes = 32 replicas, 512-token prompts, 256-token generations, `--ignore-eos`)

| profile | concurrency | generated tok/s | total tok/s | p50 latency |
|---|---|---|---|---|
| throughput | 512 | 7328 | 25470 | 14.4 s |
| throughput | 1024 | 9248 | 32150 | 18.8 s |
| **balanced** | 512 | **8018** | 27867 | 11.9 s |
| **balanced** | 1024 | **9588** | 33330 | 16.1 s |

`balanced` is faster *and* lower-latency than `throughput` while doubling the window,
so it is the default. Throughput is still climbing at 1024 concurrent requests
(= 32 replicas × 16 slots is 512 slots; beyond that requests queue and latency grows
roughly linearly). Aggregate token space: 32 × 512k = **16.8M tokens** resident;
`PROFILE=context` raises that to 32 × 2.048M = **65.5M**.

Accuracy note: what is measured above is throughput. Q8_0 weights and greedy decoding
are the accuracy-relevant choices that *are* fixed; the KV quantisation step from
`turbo2` to `turbo3` (and `accuracy`'s f16) is a faithfulness improvement that has
**not** been benchmarked here against a task suite.

## Things that bit us, and why the scripts look like this

- **Cray compiler wrappers.** CMake picks up `cc`/`CC`, which inject libsci and MPI;
  the resulting binary dies with `cannot allocate memory in static TLS block`.
  `build.sh` pins `CMAKE_C_COMPILER`/`CMAKE_CXX_COMPILER` to ROCm clang and disables
  the BLAS/LAPACK/MPI finds.
- **One job per GPU, not per node.** Setting `ROCR_VISIBLE_DEVICES` *and*
  `HIP_VISIBLE_DEVICES` made every server past GPU 0 select an empty device set and
  fall back to CPU inference — 30 tok/s prefill instead of ~800, a 23× loss overall.
  Flux binds the GPU when submitted with `-g1`; the script sets neither variable.
- **Core reservation.** GPU jobs take 22 of 96 cores so the gateway job still fits on
  a serving node; requesting all 96 left the gateway pending forever.
- **Orphan reaping.** `flux cancel` kills the wrapper but not always the server, and
  an orphan holding port 8050-8053 makes the next launch die with
  `exiting due to HTTP server error`. Every server writes
  `logs/pids/<host>-<port>.pid`; `stop.sh` cancels jobs then runs `reap-node.sh` on
  every node (`flux run --tasks-per-node 1 -N <nodes>`), which kills only pids that
  are still ours and still the `build-mi300a/bin/llama-server` executable.
- **`flux batch` copies the script** to a jobtmp dir, so `readlink -f "$0"` is wrong;
  scripts source `env.sh` by absolute path via `$LLM_SCRIPTS`.
- **LiteLLM needs `fastapi==0.115.x`** — newer FastAPI dropped `get_flat_dependant`.
- **MTP speculation is off.** This fork rejects the ggml-org `mtp-*.gguf` sidecar
  (`blk.0.attn_norm.weight not found`) and the main GGUF has no MTP layers. Re-enable
  with `NEMOTRON_MTP=1` if a compatible sidecar shows up.
