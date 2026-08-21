#!/usr/bin/env python3
"""Load-generator for the gateway: aggregate throughput at a given concurrency.

    tuolumne-llm/bench.sh <host> [--port 4000] [--conc 32] [--max-tokens 256]
                          [--prompt-tokens 512] [--model nemotron-3.5]

Reports wall-clock aggregate generation rate, per-request latency, and the
prompt/generation split, so profiles can be compared on the same footing.
"""
import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

p = argparse.ArgumentParser()
p.add_argument("host")
p.add_argument("--port", type=int, default=4000)
p.add_argument("--conc", type=int, default=32)
p.add_argument("--max-tokens", type=int, default=256)
p.add_argument("--prompt-tokens", type=int, default=512)
p.add_argument("--model", default="nemotron-3.5")
p.add_argument("--key", default="sk-tuolumne")
p.add_argument("--ignore-eos", action="store_true",
               help="generate exactly --max-tokens per request (clean TG measurement)")
a = p.parse_args()

FILLER = ("The Sierra Nevada batholith formed over tens of millions of years. " * 200).split()
prompt = " ".join(FILLER[: a.prompt_tokens]) + "\n\nSummarise the passage above."


def one(i):
    payload = {
        "model": a.model,
        "max_tokens": a.max_tokens,
        "messages": [{"role": "user", "content": f"[{i}] {prompt}"}],
    }
    if a.ignore_eos:
        payload["ignore_eos"] = True
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://{a.host}:{a.port}/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {a.key}"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.loads(r.read())
    u = d.get("usage", {})
    return time.time() - t0, u.get("completion_tokens", 0), u.get("prompt_tokens", 0)


t0 = time.time()
with ThreadPoolExecutor(max_workers=a.conc) as ex:
    res = list(ex.map(one, range(a.conc)))
wall = time.time() - t0

lat = [r[0] for r in res]
gen = sum(r[1] for r in res)
pro = sum(r[2] for r in res)
print(f"concurrency      {a.conc}")
print(f"wall clock       {wall:.1f} s")
print(f"prompt tokens    {pro}")
print(f"generated tokens {gen}")
print(f"aggregate gen    {gen / wall:.1f} tok/s")
print(f"aggregate total  {(gen + pro) / wall:.1f} tok/s (prompt + generated)")
print(f"latency p50/p95  {statistics.median(lat):.1f} s / {sorted(lat)[int(len(lat) * 0.95) - 1]:.1f} s")
