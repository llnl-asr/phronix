# llama.cpp inference fleet on corona (MI50 / gfx906)

The same fleet as `tuolumne-llm/`, on the cluster you can actually get an
allocation on.

Every script here except `env.sh`, `setup.sh` and this file is a **symlink** to
its Tuolumne counterpart. Each one resolves `env.sh` next to *itself*, so
sourcing this directory's `env.sh` is what makes a shared script a corona
script. Fix a bug in `deploy.sh` and both clusters get it.

```bash
corona-llm/setup.sh                                   # once: venv, clone, models
flux batch -N1 -t 60m --queue=pdebug \
    --output=$LLM_ROOT/logs/build.log corona-llm/build.sh   # once: gfx906 build

flux proxy <alloc-jobid> corona-llm/deploy.sh         # START
corona-llm/status.sh                                  # live view
flux proxy <alloc-jobid> corona-llm/stop.sh           # STOP
```

## What is different from Tuolumne, and why it matters

| | Tuolumne | corona |
|---|---|---|
| GPU | 4 x MI300A (gfx942, CDNA3) | **8 x MI50/MI60 (gfx906, Vega20)** |
| Memory per GPU | 128 GB unified, 5.3 TB/s | **32 GB discrete, 1.0 TB/s** |
| Cores per node | 96 | **48** (2 x EPYC 7402) |
| ROCm | 7.2.1 | **5.7.1** |
| Staging disk | `/l/ssd` | `/l/ssd` (3.5 TB NVMe) |
| Data root | `/p/lustre5/haridev/llm-tuolumne` | `/p/lustre3/haridev/llm-corona` |
| Gateway key | `sk-tuolumne` | `sk-corona` |

Four of those are not preferences:

**ROCm 5.7.1 is forced.** gfx906 was dropped from rocBLAS after the 5.x line.
Check before changing it:

```bash
for v in 5.7.1 6.0.3 6.1.3 6.2.0 6.4.3; do
    echo -n "$v: "; ls /opt/rocm-$v/lib/rocblas/library/ 2>/dev/null | grep -c gfx906
done
# 5.7.1: 156   6.0.3: 0   6.1.3: 0   6.2.0: 0   6.4.3: 0
```

A build against 6.x or 7.x compiles cleanly and then finds no kernels for the
device at runtime.

**MFMA is compiled out.** Matrix cores are a CDNA feature (gfx908+); gfx906 is
GCN and has none, so `build.sh` gets `HIP_MMQ_MFMA=OFF` from `env.sh`. HIP
graphs are off for the same reason — least-exercised path on a deprecated arch,
and worth nothing at one request per slot.

**Flash attention is `auto`, not `on`.** llama.cpp's HIP flash-attention
kernels do not cover gfx906, and `on` fails the server at startup rather than
falling back.

**32 GB per card decides which models can run at all.**

| model | size | how it runs here |
|---|---|---|
| `gptoss20` | ~12 GB | fits one GPU — 8 replicas per node (the default) |
| `gptoss120` | ~63 GB | does **not** fit one GPU — one server sharded across all 8 |

The 30B-A3B Q8_0 models Tuolumne serves are ~32 GB, which is the whole card
with nothing left for KV. They are absent from `env.sh` rather than listed and
broken.

```bash
# 8 replicas of gpt-oss-20b per node (the default)
flux proxy <alloc> corona-llm/deploy.sh gptoss20

# gpt-oss-120b: ONE server per node, sharded across all eight cards
GPUS_PER_NODE=1 GPUS_PER_SERVER=8 CORES_PER_SERVER=44 \
    flux proxy <alloc> corona-llm/deploy.sh gptoss120
```

`GPUS_PER_NODE` counts **servers** per node; `GPUS_PER_SERVER` is how many GPUs
each gets. Sharding trades eight independent replicas for one — on a 32 GB card
that is not a choice, the alternative is a server that dies part-way through
loading its weights.

## Getting an allocation

```bash
flux alloc -N4 -t 12h --queue=pbatch     # pdebug caps at 1h; pbatch for real runs
flux resource list                       # what is free right now
```

`pdebug` is 13 nodes and usually free, which makes it the right queue for a
build or a one-node smoke test. Everything else wants `pbatch`.

Inside an allocation, do **not** pass `-t` to anything: a job inherits the
instance's lifetime and naming a longer one is refused outright.

## Pointing the benchmark at this fleet

`deploy.sh` writes `corona-llm/cluster.json`, and every consumer takes the
fleet directory from `PHRONIX_FLEET`:

```bash
PHRONIX_FLEET=corona-llm scripts/run-group.sh --local --size 6 1
PHRONIX_FLEET=corona-llm scripts/bench_top.py
PHRONIX_FLEET=corona-llm corona-llm/status.sh
```

Unset, everything still defaults to `tuolumne-llm` exactly as before. An
explicit `--cluster <path>` beats both.

## The `corona` server profile

`PROFILE=corona` (the default here, via `FLEET_PROFILE`) is `solo` resized for
a 32 GB discrete card: one slot, the trained 131,072-token window, **f16 KV**
rather than turboquant, and 2048-token batches instead of 4096.

The one-slot argument is inherited unchanged and is about eviction, not memory:
the prompt cache is per slot, and an agent that loses its prefix pays full
prefill again. What is corona-specific is everything sized against 128 GB of
unified memory — a 63 GB model plus a half-million-token KV pool on one device
does not fit here, and llama.cpp does not fail politely when it runs out. It
allocates until the card is full and dies mid-load.

f16 KV rather than `turbo4`/`turbo3`: at one slot and 131,072 tokens the KV is
single-digit GB either way, so quantising it on the least-exercised code path
for this architecture buys nothing.
