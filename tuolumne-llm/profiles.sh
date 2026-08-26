#!/bin/bash
# Server tuning profiles for MI300A (128 GB unified HBM per APU, 4 per node).
# Selected with PROFILE=throughput|context|accuracy (default: throughput).
#
# Fixed across profiles: Q8_0 weights (8-bit, per the notes), greedy decoding
# (temp 0 / top-k 1 / no penalties) so results are deterministic and comparable.
#
#   throughput  many concurrent slots, moderate context, aggressive prefill batch
#               and prompt-cache reuse. Maximises aggregate tokens/s.
#   context     maximum token space: 4-bit K / 2-bit V turboquant KV, unified KV,
#               fewer slots so each gets a huge window.
#   accuracy    lossless f16 KV cache, fewer slots, no prompt-cache reuse, so no
#               quantisation or reuse artefacts enter attention.
#   solo        ONE request per GPU, 131k window, f16 KV. Nothing shares a slot,
#               so a conversation's prompt cache is never evicted by another
#               agent's. Use when prefill dominates GPU time (it did: 77%).
#   agent       256k per request, 4 per GPU, sized to leave room for large weights
#               (gpt-oss-120b is 63 GB). The default for SWE-agent runs.
#   wide        1M tokens per request, 4 per GPU (128 across the node set), 4-bit K
#               / 3-bit V KV. For agent workloads whose prompts run to hundreds of
#               thousands of tokens and are truncated by the other profiles.
#   balanced    the recommended default: 16 slots, 512k window per replica, 4-bit K
#               / 3-bit V KV (one step more faithful than the throughput profile's
#               2-bit V), full-size prefill batches and prompt-cache reuse.
profile_args() {
    case "${PROFILE:-balanced}" in
        solo)
            # One agent per GPU. Nothing shares a slot, so nothing evicts.
            #
            # This is a cache profile, not a capacity profile. Measured on a
            # live backend under the `agent` profile (4 slots):
            #
            #   prompt    2,314,160 tokens in 957 s
            #   generated    33,441 tokens in 278 s
            #
            # Prefill was 77% of GPU time and the fleet processed 69 prompt
            # tokens for every generated one — i.e. it was re-reading contexts
            # it had already read. A cached prefix costs 0.3 s where a cold one
            # costs 11.1 s, so almost all of that 957 s was avoidable.
            #
            # The cause is that the prompt cache is per SLOT. Four agents on
            # one server hold four unrelated conversations, and each new
            # request evicts whichever prefix it displaces; an agent returning
            # for its next turn finds its own prefix gone and pays full prefill
            # again. Pinning a task to a backend is necessary for cache reuse
            # but not sufficient, because the eviction happens inside the
            # backend.
            #
            # One slot makes the cache private: a slot holds exactly one
            # conversation, and that conversation is the only thing that can
            # displace it.
            #
            # The capacity given up is nominal, not real. This trades 128
            # concurrent requests for 32 — and the fleet has been running 3-22
            # in flight, with 29 of 32 backends idle, so the slots being
            # surrendered were never occupied. A single slot also gets the
            # whole 131,072 window without dividing a pool, which removes the
            # `-c ÷ --parallel` truncation trap entirely.
            #
            # Three cache controls, and they do different jobs:
            #
            #   --cache-reuse 1024  reuse a prefix that has DIVERGED. An agent
            #                       turn is the previous turn plus a tool
            #                       result, so the common prefix is nearly the
            #                       whole context; a larger chunk size lets
            #                       more of it survive the divergence.
            #   --cache-ram 24576   keep evicted conversations in RAM instead
            #                       of discarding them. This is what makes one
            #                       slot safe: a second conversation reaching
            #                       this backend parks the first rather than
            #                       destroying it, and restoring costs a copy
            #                       instead of 11 s of prefill.
            #   f16 KV              no quantisation artefacts in the cache we
            #                       are making authoritative — affordable now
            #                       that one context sits beside the weights
            #                       instead of four.
            #
            # 24 GiB per server, i.e. 96 GiB of the node's 501 GiB spent on
            # not re-reading text we have already read. Measured on a fleet
            # node: 501 total, 365 used by four servers, 126 available — so
            # four servers at 24 GiB fit with room left, where `-cram -1` would
            # race the weights for unified memory and lose unpredictably.
            #
            # This is the setting to raise first if the cache still misses:
            # the log reports how much of it is in use, and headroom above is
            # measured, not assumed.
            # Slots are a knob because one is not obviously right.
            #
            # Measured at LLAMA_SLOTS=1: the cache problem is solved (69 prompt
            # tokens per generated one fell to 6, prefill's share of GPU time
            # from 77% to 60%) and a capacity problem takes its place — 9
            # requests in flight, 31 QUEUED, 23 backends idle. One slot per GPU
            # caps the fleet at 32 concurrent requests, and two arms times six
            # tasks times an eight-wide research fanout wants more.
            #
            # LLAMA_SLOTS=2 is the answer to that, and it is not a return to
            # the old failure: what made four slots bad was eviction DESTROYING
            # a prefix, and --cache-ram now parks the evicted conversation
            # instead, so the cost is a memory copy rather than 11 s of
            # re-prefill. The protection that was missing then exists now.
            #
            # `-c` is multiplied to match, because -c is a pool that --parallel
            # divides: slots x 131072 keeps every slot at the trained window.
            echo "--parallel ${LLAMA_SLOTS:-1}
                  -c ${LLAMA_CTX:-$(( ${LLAMA_SLOTS:-1} * 131072 ))}
                  --cache-type-k f16 --cache-type-v f16 --kv-unified
                  --batch-size 4096 --ubatch-size 4096
                  --cache-ram 24576 --cache-reuse 1024
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        agent)
            # For agent workloads on a large-weights model.
            #
            # Sized to the model's TRAINING context, not the hardware ceiling.
            #
            # 4 x 131,072 = 524,288. gpt-oss-120b was trained to 131,072, and
            # asking a slot for more makes llama.cpp extend with rope scaling:
            #
            #   n_ctx_seq (262144) > n_ctx_train (131072) -- possible overflow
            #   the slot context exceeds the training context - using rope
            #   scaling to extend
            #
            # That rescales position encodings for every request, not just long
            # ones, so it degrades short prompts to buy length nothing here
            # wants: the client already caps conversations at 131,072 because
            # quality fell when they ran to 155k. Staying inside the trained
            # window is free accuracy and halves the KV beside 63 GB of weights.
            echo "--parallel 4 -c ${LLAMA_CTX:-524288}
                  --cache-type-k turbo4 --cache-type-v turbo3 --kv-unified
                  --batch-size 4096 --ubatch-size 4096
                  --cache-ram 4096 --cache-reuse 256
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        wide)
            # 1M tokens per REQUEST, four requests at a time, per GPU.
            #
            # `-c` is the pool and `--parallel` divides it: the running fleet at
            # `--parallel 16 -c 524288` gives each slot 32768, which is what
            # /props reports and what agent requests were being truncated at.
            # So 1M per slot means 4 x 1M = 4194304 in the pool.
            #
            # Four slots rather than eight: 4M of KV is already twice what the
            # `context` profile allocates, and per-GPU HBM is the limit that
            # bites first. Across 32 GPUs this is still 128 concurrent requests,
            # each with a megabyte of context.
            #
            # turbo3 for V rather than turbo2: one step more faithful, and the
            # accuracy cost of 2-bit V is the one most visible in long-context
            # work, which is exactly what this profile is for.
            echo "--parallel 4 -c ${LLAMA_CTX:-4194304}
                  --cache-type-k turbo4 --cache-type-v turbo3 --kv-unified
                  --batch-size 4096 --ubatch-size 4096
                  --cache-ram 4096 --cache-reuse 256
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        balanced)
            echo "--parallel 16 -c ${LLAMA_CTX:-524288}
                  --cache-type-k turbo4 --cache-type-v turbo3 --kv-unified
                  --batch-size 4096 --ubatch-size 4096
                  --cache-ram 4096 --cache-reuse 256
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        throughput)
            echo "--parallel 32 -c ${LLAMA_CTX:-262144}
                  --cache-type-k turbo4 --cache-type-v turbo2 --kv-unified
                  --batch-size 4096 --ubatch-size 4096
                  --cache-ram 4096 --cache-reuse 256
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        context)
            echo "--parallel 8 -c ${LLAMA_CTX:-2048000}
                  --cache-type-k turbo4 --cache-type-v turbo2 --kv-unified
                  --batch-size 2048 --ubatch-size 4096
                  --cache-ram 2048 --cache-reuse 256
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        accuracy)
            echo "--parallel 8 -c ${LLAMA_CTX:-131072}
                  --cache-type-k f16 --cache-type-v f16 --kv-unified
                  --batch-size 2048 --ubatch-size 2048
                  --cache-ram 1024
                  -t ${LLAMA_THREADS:-22} -tb ${LLAMA_THREADS:-22}" ;;
        corona)
            # corona: 8 x MI50/MI60 (gfx906), 32 GB DISCRETE HBM per card.
            #
            # A separate profile because every other one here was sized against
            # Tuolumne's 128 GB unified APU memory, where a 63 GB model and a
            # half-million-token KV pool sit on one device. On a 32 GB card the
            # same numbers do not fit, and llama.cpp does not fail politely: it
            # allocates until the device is out and dies mid-load.
            #
            # One slot, as `solo`, and for the same reason — the prompt cache
            # is per slot, and an agent that loses its prefix pays full prefill
            # again. That argument is about eviction, not about memory, so it
            # transfers unchanged.
            #
            # f16 KV rather than turboquant: gfx906 is a 2018 part and the
            # turbo* cache types are the least-exercised path on it. At one
            # slot and the trained 131,072 window the KV is single-digit GB
            # either way, so there is nothing to buy by quantising it.
            #
            # Batches are half Tuolumne's: 4096-token ubatches are sized for
            # HBM bandwidth this card does not have (1.0 TB/s against 5.3),
            # and the compute buffer for them is charged against the same
            # 32 GB the weights are in.
            echo "--parallel ${LLAMA_SLOTS:-1}
                  -c ${LLAMA_CTX:-$(( ${LLAMA_SLOTS:-1} * 131072 ))}
                  --cache-type-k f16 --cache-type-v f16 --kv-unified
                  --batch-size 2048 --ubatch-size 2048
                  --cache-ram 8192 --cache-reuse 1024
                  --ctx-checkpoints 8 --checkpoint-min-step 16384
                  -t ${LLAMA_THREADS:-6} -tb ${LLAMA_THREADS:-6}" ;;
        *) echo "unknown PROFILE '$PROFILE' (solo|agent|wide|balanced|throughput|context|accuracy|corona)" >&2; return 1 ;;
    esac
}
