#!/usr/bin/env python3
"""Fleet performance over a NAMED WINDOW: what the GPUs did while a job ran.

    tuolumne-llm/session.sh start [name]    # mark now as the start, begin sampling
    tuolumne-llm/session.sh stop  [name]    # close the window and print the report
    tuolumne-llm/session.sh report [name]   # the report so far, without closing
    tuolumne-llm/session.sh list            # sessions on disk, newest first
    tuolumne-llm/session.sh poll <dir>      # the sampler itself (started by `start`)

`name` defaults to the open session (`sessions/current`), so a benchmark can
bracket itself with a bare `start` and a bare `stop`.

WHY A SESSION AND NOT `status.sh`
---------------------------------
Every llama-server counter is cumulative since the server booted, so a live
display can only ever answer "what is happening now" and "what has happened
since the fleet came up". Neither is the question a benchmark asks, which is
"what did the fleet do during MY run" — and the fleet is usually up before the
run starts and stays up after it ends, so the lifetime figures include work that
is not the run's.

A session is two snapshots and the samples in between:

  * counters (prompt tokens, generated tokens, prefill/decode seconds, decode
    iterations) are DIFFERENCED end-minus-start, which is exact;
  * gauges (requests in flight, deferred) and the prompt cache are SAMPLED,
    because they have no cumulative counter to difference — so those figures are
    averages and peaks over the sampling grid, and are labelled as such.

PROMPT CACHE
------------
llama.cpp publishes no cache counter in /metrics; the information is per-slot in
/slots, as `n_prompt_tokens_cache` against `n_prompt_tokens` for the request the
slot is currently serving. The sampler records each (replica, slot, task-id) it
sees once, so the totals are over REQUESTS OBSERVED, not all requests: a request
that begins and ends between two samples is invisible. It is a hit-rate estimate
on a large sample, not an audit — treat a few points of drift as noise.

A RESTARTED REPLICA
-------------------
A server that restarts mid-session resets its counters to zero, so end-minus-
start goes negative. Those replicas are counted as restarted, their delta is
taken as the end value alone (everything it has done since it came back), and
the report says how many — silently clamping to zero would understate the fleet
and silently keeping the negative would corrupt every total above it.
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

LLM_ROOT = os.environ.get("LLM_ROOT", "/p/lustre5/haridev/llm-tuolumne")
HERE = os.path.dirname(os.path.abspath(__file__))
SESSIONS = os.path.join(LLM_ROOT, "logs", "sessions")
INTERVAL = float(os.environ.get("SESSION_INTERVAL", "5"))

COUNTERS = ("prompt_tokens_total", "tokens_predicted_total", "n_decode_total",
            "prompt_seconds_total", "tokens_predicted_seconds_total",
            "spec_decode_num_draft_tokens_total",
            "spec_decode_num_accepted_tokens_total")
GAUGES = ("requests_processing", "requests_deferred", "n_busy_slots_per_decode")


# ---- the fleet, as it is right now -------------------------------------------
# Same rule as status.sh: the newest config, and its membership taken from the
# per-GPU records if the config was written before the servers registered.
def cluster_cfg():
    cands = [os.path.join(HERE, "cluster.json"),
             os.path.join(LLM_ROOT, "logs", "cluster.json")]
    cands = [c for c in cands if os.path.exists(c)]
    if not cands:
        sys.exit("no cluster config found — is a fleet running?")

    def stamp(path):
        try:
            with open(path) as f:
                return os.path.basename(json.load(f).get("run_dir", ""))
        except Exception:
            return ""

    with open(max(cands, key=stamp)) as f:
        cfg = json.load(f)
    servers = [s for s in cfg.get("servers") or [] if s]
    if not servers:
        d = os.path.join(cfg.get("run_dir", ""), "nodes")
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".json"):
                    try:
                        with open(os.path.join(d, name)) as f:
                            servers.append(json.load(f))
                    except Exception:
                        pass
    cfg["servers"] = servers
    return cfg


def get_json(url, timeout=4):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def get_metrics(server):
    url = f"http://{server['host']}:{server['port']}/metrics"
    out = {}
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            for line in r.read().decode().splitlines():
                if not line.startswith("llamacpp:"):
                    continue
                key, _, val = line.partition(" ")
                key = key.split(":", 1)[1]
                if key in COUNTERS or key in GAUGES:
                    out[key] = float(val)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return out


def sample_one(server):
    """One replica: its counters, its gauges, and whatever its slots are doing."""
    key = f"{server['host']}:{server['port']}"
    metrics = get_metrics(server)
    row = {"replica": key, "host": server["host"], "port": server["port"],
           "up": metrics is not None, "metrics": metrics or {}, "slots": []}
    slots = get_json(f"http://{server['host']}:{server['port']}/slots")
    if isinstance(slots, list):
        for s in slots:
            if not s.get("is_processing"):
                continue
            row["slots"].append({
                "slot": s.get("id"),
                "task": s.get("id_task"),
                "prompt": s.get("n_prompt_tokens", 0),
                "processed": s.get("n_prompt_tokens_processed", 0),
                "cached": s.get("n_prompt_tokens_cache", 0),
            })
    return row


def snapshot(servers):
    with ThreadPoolExecutor(max_workers=max(1, min(64, len(servers)))) as ex:
        rows = list(ex.map(sample_one, servers))
    return {"t": time.time(), "replicas": rows}


# ---- sessions on disk --------------------------------------------------------
def session_dir(name=None, must_exist=True):
    if name:
        d = os.path.join(SESSIONS, name)
    else:
        d = os.path.join(SESSIONS, "current")
        if not os.path.exists(d):
            sys.exit("no open session — start one with: session.sh start <name>")
        d = os.path.realpath(d)
    if must_exist and not os.path.isdir(d):
        sys.exit(f"no such session: {os.path.basename(d)}")
    return d


def cmd_start(name):
    os.makedirs(SESSIONS, exist_ok=True)
    name = name or time.strftime("session-%Y%m%d-%H%M%S")
    d = os.path.join(SESSIONS, name)
    os.makedirs(d, exist_ok=True)
    cfg = cluster_cfg()
    start = snapshot(cfg["servers"])
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump({"name": name, "started": start["t"], "interval": INTERVAL,
                   "alias": cfg.get("alias"), "profile": cfg.get("profile"),
                   "run_dir": cfg.get("run_dir"),
                   "gateway": cfg.get("gateway", {}),
                   "replicas": len(cfg["servers"])}, f, indent=2)
    with open(os.path.join(d, "start.json"), "w") as f:
        json.dump(start, f)
    # Truncate: restarting a session name should not inherit the old window's
    # samples, which would be dated before its own start and silently widen it.
    open(os.path.join(d, "samples.jsonl"), "w").close()
    open(os.path.join(d, "requests.jsonl"), "w").close()

    # The sampler outlives this process — `start` returns to the caller (a
    # benchmark script) and the window stays open until `stop`.
    log = open(os.path.join(d, "poll.log"), "a")
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "poll", d],
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    with open(os.path.join(d, "poller.pid"), "w") as f:
        f.write(str(p.pid))
    link = os.path.join(SESSIONS, "current")
    tmp = link + ".tmp"
    os.symlink(d, tmp)
    os.replace(tmp, link)
    up = sum(1 for r in start["replicas"] if r["up"])
    print(f"session {name} open: {up}/{len(start['replicas'])} replica(s), "
          f"sampling every {INTERVAL:g}s")
    print(f"  {d}")
    return 0


def cmd_poll(d):
    seen = set()   # (replica, slot, task) — a request is recorded once
    reqs = open(os.path.join(d, "requests.jsonl"), "a")
    samples = open(os.path.join(d, "samples.jsonl"), "a")
    cfg = cluster_cfg()
    stop = os.path.join(d, "STOP")
    while not os.path.exists(stop):
        snap = snapshot(cfg["servers"])
        thin = {"t": snap["t"], "r": []}
        for row in snap["replicas"]:
            m = row["metrics"]
            thin["r"].append([row["replica"], int(row["up"]),
                              m.get("requests_processing", 0),
                              m.get("requests_deferred", 0)])
            for s in row["slots"]:
                key = (row["replica"], s["slot"], s["task"])
                if key in seen:
                    continue
                seen.add(key)
                reqs.write(json.dumps({"t": snap["t"], "replica": row["replica"],
                                       **s}) + "\n")
        samples.write(json.dumps(thin) + "\n")
        samples.flush()
        reqs.flush()
        time.sleep(INTERVAL)
    return 0


def cmd_stop(name):
    d = session_dir(name)
    cfg = cluster_cfg()
    end = snapshot(cfg["servers"])
    with open(os.path.join(d, "end.json"), "w") as f:
        json.dump(end, f)
    # Ask the sampler to finish its cycle, then make sure it did. A sampler left
    # running writes into the next session's window as well as this one.
    open(os.path.join(d, "STOP"), "w").close()
    pidfile = os.path.join(d, "poller.pid")
    if os.path.exists(pidfile):
        try:
            pid = int(open(pidfile).read().strip())
            for _ in range(int(INTERVAL * 2) + 4):
                os.kill(pid, 0)
                time.sleep(1)
            os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError):
            pass
    link = os.path.join(SESSIONS, "current")
    if os.path.islink(link) and os.path.realpath(link) == d:
        os.unlink(link)
    text = report(d)
    with open(os.path.join(d, "report.txt"), "w") as f:
        f.write(text + "\n")
    print(text)
    return 0


def cmd_report(name):
    print(report(session_dir(name)))
    return 0


def cmd_list():
    if not os.path.isdir(SESSIONS):
        print("no sessions yet")
        return 0
    rows = []
    for name in os.listdir(SESSIONS):
        d = os.path.join(SESSIONS, name)
        if name == "current" or not os.path.isdir(d) or os.path.islink(d):
            continue
        try:
            meta = json.load(open(os.path.join(d, "meta.json")))
        except (OSError, ValueError):
            continue
        closed = os.path.exists(os.path.join(d, "end.json"))
        rows.append((meta.get("started", 0), name, meta, closed))
    for started, name, meta, closed in sorted(rows, reverse=True):
        state = "closed" if closed else "OPEN"
        print(f"  {name:<32} {state:<7} {meta.get('alias', '?'):<16} "
              f"{time.strftime('%m-%d %H:%M', time.localtime(started))}")
    return 0


# ---- the report --------------------------------------------------------------
def human(n):
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


def hms(s):
    s = int(s or 0)
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


def fairness(values):
    """Jain's index: 1.0 = every replica did the same amount, 1/n = one did it all."""
    vals = [v for v in values if v >= 0]
    if not vals or sum(vals) <= 0:
        return None
    n = len(vals)
    return sum(vals) ** 2 / (n * sum(v * v for v in vals))


def report(d):
    meta = json.load(open(os.path.join(d, "meta.json")))
    start = json.load(open(os.path.join(d, "start.json")))
    end_path = os.path.join(d, "end.json")
    if os.path.exists(end_path):
        end, closed = json.load(open(end_path)), True
    else:
        end, closed = snapshot(cluster_cfg()["servers"]), False

    window = max(1e-9, end["t"] - start["t"])
    first = {r["replica"]: r for r in start["replicas"]}
    restarted = 0
    per_replica, totals = {}, dict.fromkeys(COUNTERS, 0.0)
    for row in end["replicas"]:
        a = first.get(row["replica"], {}).get("metrics", {})
        b = row["metrics"]
        delta = {}
        rebooted = False
        for k in COUNTERS:
            d0, d1 = a.get(k, 0.0), b.get(k, 0.0)
            if d1 < d0:          # counters only ever rise; this one restarted
                rebooted = True
                delta[k] = d1
            else:
                delta[k] = d1 - d0
        restarted += rebooted
        per_replica[row["replica"]] = delta
        for k in COUNTERS:
            totals[k] += delta[k]

    # gauges, over the sampling grid
    inflight, deferred, busy_samples, n_samples = [], [], 0, 0
    for line in open(os.path.join(d, "samples.jsonl"), errors="ignore"):
        try:
            s = json.loads(line)
        except ValueError:
            continue
        n_samples += 1
        run = sum(r[2] for r in s["r"])
        inflight.append(run)
        deferred.append(sum(r[3] for r in s["r"]))
        busy_samples += 1 if run > 0 else 0

    # prompt cache, over the requests the sampler caught
    n_req = prompt_tok = cached_tok = 0
    rpath = os.path.join(d, "requests.jsonl")
    if os.path.exists(rpath):
        for line in open(rpath, errors="ignore"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            n_req += 1
            prompt_tok += r.get("prompt", 0)
            cached_tok += r.get("cached", 0)

    nrep = len(end["replicas"])
    up = sum(1 for r in end["replicas"] if r["up"])
    L = []
    L.append(f"session {meta['name']}  [{'closed' if closed else 'OPEN'}]  "
             f"{meta.get('alias', '?')}  profile {meta.get('profile', '?')}")
    L.append(f"  window       {hms(window)}  "
             f"({time.strftime('%H:%M:%S', time.localtime(start['t']))} -> "
             f"{time.strftime('%H:%M:%S', time.localtime(end['t']))})  "
             f"{up}/{nrep} replica(s) up"
             + (f"  {restarted} RESTARTED" if restarted else ""))
    L.append("")
    p, g = totals["prompt_tokens_total"], totals["tokens_predicted_total"]
    ps, gs = totals["prompt_seconds_total"], totals["tokens_predicted_seconds_total"]
    L.append(f"  tokens       prompt {human(p):>8}   generated {human(g):>8}   "
             f"total {human(p + g):>8}")
    L.append(f"  fleet rate   prompt {p / window:8.0f} tok/s   "
             f"generated {g / window:8.0f} tok/s   (over the whole window)")
    # Busy-time rates say how fast the GPUs are when they are working; the fleet
    # rate above says how much of the window they spent working. Reporting only
    # one of the two makes an idle fleet look slow, or a slow one look idle.
    if ps > 0:
        L.append(f"  when busy    prefill {p / ps:8.0f} tok/s   "
                 f"decode {(g / gs if gs else 0):8.0f} tok/s   "
                 f"(prefill {ps / max(window * max(nrep, 1), 1e-9) * 100:.1f}% of "
                 f"fleet-seconds, decode "
                 f"{gs / max(window * max(nrep, 1), 1e-9) * 100:.1f}%)")
    if prompt_tok:
        L.append(f"  prompt cache {cached_tok / prompt_tok * 100:5.1f}% of prompt "
                 f"tokens reused   ({human(cached_tok)} of {human(prompt_tok)} "
                 f"over {n_req} sampled request(s))")
    else:
        L.append("  prompt cache no requests sampled")
    if n_samples:
        L.append(f"  concurrency  mean {sum(inflight) / n_samples:5.1f} in flight   "
                 f"peak {max(inflight):3.0f}   "
                 f"deferred peak {max(deferred):3.0f}   "
                 f"fleet busy {busy_samples / n_samples * 100:.0f}% of "
                 f"{n_samples} sample(s)")
        # Utilisation against slots, not against replicas: a `solo` fleet has one
        # slot per GPU, so "8 in flight" on 8 replicas is FULL, not merely busy.
        L.append(f"  utilisation  {sum(inflight) / n_samples / max(nrep, 1) * 100:5.1f}% "
                 f"of {nrep} replica-slot(s) occupied on average")
    else:
        L.append("  concurrency  no samples (was the poller running?)")
    fi = fairness([v["n_decode_total"] for v in per_replica.values()])
    if fi is not None:
        L.append(f"  balance      {fi:.3f} Jain over {nrep} replicas "
                 f"({'even' if fi > 0.9 else 'uneven' if fi > 0.6 else 'lopsided'})")
    L.append("")
    L.append(f"  {'REPLICA':<24}{'PROMPT':>10}{'GEN':>10}{'DECODES':>10}{'SHARE':>8}")
    dec_total = sum(v["n_decode_total"] for v in per_replica.values()) or 1
    for key in sorted(per_replica):
        v = per_replica[key]
        L.append(f"  {key:<24}{human(v['prompt_tokens_total']):>10}"
                 f"{human(v['tokens_predicted_total']):>10}"
                 f"{human(v['n_decode_total']):>10}"
                 f"{v['n_decode_total'] / dec_total * 100:7.1f}%")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    rest = args[1:]
    if cmd == "start":
        return cmd_start(rest[0] if rest else None)
    if cmd == "stop":
        return cmd_stop(rest[0] if rest else None)
    if cmd == "report":
        return cmd_report(rest[0] if rest else None)
    if cmd == "list":
        return cmd_list()
    if cmd == "poll":
        return cmd_poll(rest[0])
    sys.exit(__doc__.split("\n\n")[0] + "\n\nusage: see the top of this file")


if __name__ == "__main__":
    sys.exit(main())
