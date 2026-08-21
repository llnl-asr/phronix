#!/usr/bin/env python3
"""top-like live view of the llama.cpp cluster: throughput, load and balance.

    tuolumne-llm/status.sh                 # live aggregated view (one row per node)
    tuolumne-llm/status.sh --per-gpu       # start expanded, one row per replica
    tuolumne-llm/status.sh --once          # single snapshot, no clearing
    tuolumne-llm/status.sh --interval 5    # refresh period (default 2s)
    tuolumne-llm/status.sh <cluster.json>  # explicit config

Keys while running:  a = toggle aggregated / all replicas,  q = quit.

Reads the cluster config written by run-cluster.sh (the in-repo cluster.json by
default) and scrapes every llama-server's /metrics endpoint in parallel. Rates are
for the last interval; the balance line says whether the gateway is spreading work
evenly across replicas.
"""
import json
import os
import select
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

LLM_ROOT = os.environ.get("LLM_ROOT", "/p/lustre5/haridev/llm-tuolumne")
REPO_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cluster.json")
DEFAULT_CFG = REPO_CFG if os.path.exists(REPO_CFG) else os.path.join(LLM_ROOT, "logs", "cluster.json")

# Token counters (prompt_tokens_total / tokens_predicted_total) only advance when a
# request *finishes*, so mid-generation they read 0. n_decode_total advances on every
# decode iteration, so it is the live "is the GPU working" signal and the basis for
# the per-replica work share. It counts iterations, not tokens (each iteration decodes
# every busy slot), so it is never presented as a token rate.
COUNTERS = ("prompt_tokens_total", "tokens_predicted_total", "n_decode_total",
            "spec_decode_num_draft_tokens_total", "spec_decode_num_accepted_tokens_total")
GAUGES = ("requests_processing", "requests_deferred", "n_tokens_max",
          "n_busy_slots_per_decode")
FIELDS = COUNTERS + GAUGES
SPARK = " ▁▂▃▄▅▆▇█"


class Keys:
    """Non-blocking single-key input, no-op when stdin is not a terminal."""

    def __enter__(self):
        self.fd = sys.stdin.fileno() if sys.stdin.isatty() else None
        if self.fd is not None:
            import termios, tty
            self.termios = termios
            self.saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.saved)

    def wait(self, timeout):
        """Sleep up to timeout seconds; return the key pressed, or None."""
        if self.fd is None:
            time.sleep(timeout)
            return None
        deadline = time.time() + timeout
        while True:
            left = deadline - time.time()
            if left <= 0:
                return None
            if select.select([sys.stdin], [], [], left)[0]:
                return sys.stdin.read(1)


def fetch(server):
    url = f"http://{server['host']}:{server['port']}/metrics"
    out = {"server": server, "up": False, "metrics": {}}
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            for line in r.read().decode().splitlines():
                if not line.startswith("llamacpp:"):
                    continue
                key, _, val = line.partition(" ")
                key = key.split(":", 1)[1]
                if key in FIELDS:
                    out["metrics"][key] = float(val)
        out["up"] = True
    except (urllib.error.URLError, OSError, ValueError) as e:
        out["error"] = str(e)
    return out


def gateway_ok(gw):
    try:
        with urllib.request.urlopen(
                f"http://{gw['host']}:{gw['port']}/health/liveliness", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def scrape(servers):
    with ThreadPoolExecutor(max_workers=min(64, len(servers))) as ex:
        return list(ex.map(fetch, servers))


def fairness(values):
    """Jain's fairness index: 1.0 = perfectly even, 1/n = one replica does it all."""
    n, s, sq = len(values), sum(values), sum(v * v for v in values)
    return (s * s) / (n * sq) if n and sq else 1.0


def verdict(fi):
    return "balanced" if fi >= 0.95 else "slightly uneven" if fi >= 0.85 else "IMBALANCED"


def bar(frac, width=10):
    filled = max(0, min(width, round(frac * width)))
    return "█" * filled + "·" * (width - filled)


def spark(frac):
    return SPARK[max(0, min(len(SPARK) - 1, round(frac * (len(SPARK) - 1))))]


def human(n):
    for unit, div in (("G", 1e9), ("M", 1e6), ("k", 1e3)):
        if n >= div:
            return f"{n / div:.1f}{unit}"
    return str(int(n))


def footer():
    if INTERACTIVE:
        print(f"\n\033[2m[a] {'aggregated view' if PER_GPU else 'all replicas'}   [q] quit\033[0m")


def render(cfg, rows, prev, dt):
    gw = cfg["gateway"]
    live = prev is not None and dt > 0
    per = []
    for row in rows:
        s, m = row["server"], row["metrics"]
        p = prev.get((s["host"], s["port"]), {}) if prev else {}
        delta = {k: max(0.0, m.get(k, 0.0) - p.get(k, 0.0)) for k in COUNTERS} if live else \
                {k: m.get(k, 0.0) for k in COUNTERS}
        per.append((row, delta))

    tot = {k: sum(d[k] for _, d in per) for k in COUNTERS}
    inflight = sum(r["metrics"].get("requests_processing", 0) for r in rows)
    deferred = sum(r["metrics"].get("requests_deferred", 0) for r in rows)
    up = sum(r["up"] for r in rows)
    # Work share / fairness ride on decode iterations while live (they move
    # continuously) and on generated tokens for the cumulative view.
    gen_key = "n_decode_total" if live else "tokens_predicted_total"
    gen_sum = tot[gen_key] or 1.0
    window = dt if live else 1.0

    gens = [d[gen_key] for _, d in per]
    work_fi = fairness(gens)
    req_fi = fairness([r["metrics"].get("requests_processing", 0) for r in rows])
    active = sum(1 for g in gens if g > 0)

    cum_p = sum(r["metrics"].get("prompt_tokens_total", 0) for r in rows)
    cum_g = sum(r["metrics"].get("tokens_predicted_total", 0) for r in rows)

    # ---- summary -------------------------------------------------------------
    print(f"\033[1m{cfg['alias']}\033[0m  profile {cfg.get('profile', '?')}  "
          f"gateway {gw['host']}:{gw['port']} [{'UP' if gateway_ok(gw) else 'DOWN'}]  "
          f"replicas {up}/{len(rows)}  "
          f"{'live, last %.1fs' % dt if live else 'cumulative since start'}")
    if live:
        busy = sum(r["metrics"].get("n_busy_slots_per_decode", 0) for r in rows)
        print(f"  throughput   prompt {tot['prompt_tokens_total'] / window:8.0f} tok/s  "
              f"generate {tot['tokens_predicted_total'] / window:8.0f} tok/s  "
              f"total {(tot['prompt_tokens_total'] + tot['tokens_predicted_total']) / window:8.0f} tok/s"
              f"   (counted as requests complete)")
        print(f"  activity     {tot['n_decode_total'] / window:8.0f} decode iters/s  "
              f"{busy:8.1f} slots busy across the fleet")
    else:
        print(f"  totals       prompt {tot['prompt_tokens_total']:9.0f} tokens  "
              f"generate {tot['tokens_predicted_total']:9.0f} tokens  "
              f"total {tot['prompt_tokens_total'] + tot['tokens_predicted_total']:9.0f} tokens")
    print(f"  load         {int(inflight):4d} in flight   {int(deferred):4d} deferred   "
          f"{active}/{len(rows)} replicas active")
    # With only a handful of requests left in flight a low fairness score says
    # nothing useful, so do not cry imbalance over a draining queue.
    if inflight < len(rows) and active < len(rows) / 2:
        print(f"  balance      too little load to judge "
              f"({int(inflight)} in flight across {len(rows)} replicas)")
    else:
        note = "" if inflight >= 2 * len(rows) else \
            f"  [light load: {int(inflight)} in flight, discount this]"
        print(f"  balance      work {work_fi:.3f} ({verdict(work_fi)})   "
              f"requests {req_fi:.3f} ({verdict(req_fi)})   "
              f"(share of {'decode work' if live else 'generated tokens'}){note}")
    print(f"  lifetime     {human(cum_p + cum_g)} tokens  "
          f"({human(cum_p)} prompt + {human(cum_g)} generated)")
    drafted = tot["spec_decode_num_draft_tokens_total"]
    if drafted:
        print(f"  speculative  {tot['spec_decode_num_accepted_tokens_total'] / drafted * 100:.1f}% "
              f"of {int(drafted)} drafted tokens accepted")
    print()

    if PER_GPU:
        hdr = (f"{'HOST':<14}{'GPU':>4}{'PORT':>6}{'PID':>9}{'ST':>5}{'RUN':>5}{'DEF':>5}"
               f"{'PP t/s' if live else 'PROMPT':>9}{'TG t/s' if live else 'GEN':>9}"
               f"{'DEC/s' if live else 'DECODES':>9}{'SHARE':>8}  BALANCE")
        print(f"\033[7m{hdr}\033[0m")
        for row, d in per:
            s, m = row["server"], row["metrics"]
            share = d[gen_key] / gen_sum
            print(f"{s['host']:<14}{s['gpu']:>4}{s['port']:>6}{s['pid']:>9}"
                  f"{'up' if row['up'] else 'DOWN':>5}"
                  f"{int(m.get('requests_processing', 0)):>5}{int(m.get('requests_deferred', 0)):>5}"
                  f"{d['prompt_tokens_total'] / window:>9.0f}"
                  f"{d['tokens_predicted_total'] / window:>9.0f}"
                  f"{d['n_decode_total'] / window:>9.0f}"
                  f"{share * 100:>7.1f}%  {bar(share * len(per))}")
        footer()
        return

    # ---- one row per node, GPUs as sparkline columns --------------------------
    nodes = {}
    for row, d in per:
        s, m = row["server"], row["metrics"]
        n = nodes.setdefault(s["host"], {"gpus": {}, "up": 0, "run": 0, "def": 0,
                                         "pp": 0.0, "tg": 0.0, "dec": 0.0, "share": 0.0})
        n["gpus"][s["gpu"]] = d[gen_key] / gen_sum
        n["up"] += row["up"]
        n["run"] += m.get("requests_processing", 0)
        n["def"] += m.get("requests_deferred", 0)
        n["pp"] += d["prompt_tokens_total"]
        n["tg"] += d["tokens_predicted_total"]
        n["dec"] += d["n_decode_total"]
        n["share"] += d[gen_key]

    ngpu = max((len(n["gpus"]) for n in nodes.values()), default=4)
    hdr = (f"{'NODE':<14}{'UP':>4}{'RUN':>5}{'DEF':>5}"
           f"{'PP t/s' if live else 'PROMPT':>10}{'TG t/s' if live else 'GEN':>10}"
           f"{'DEC/s' if live else 'DECODES':>9}"
           f"{'SHARE':>8}  {'GPU' + str(ngpu):<6} BALANCE")
    print(f"\033[7m{hdr}\033[0m")
    for host in sorted(nodes):
        n = nodes[host]
        share = n["share"] / gen_sum
        gpus = "".join(spark(n["gpus"].get(g, 0.0) * len(per)) for g in range(ngpu))
        print(f"{host:<14}{n['up']:>3}/{len(n['gpus']):<1}{int(n['run']):>5}{int(n['def']):>5}"
              f"{n['pp'] / window:>10.0f}{n['tg'] / window:>10.0f}{n['dec'] / window:>9.0f}"
              f"{share * 100:>7.1f}%  [{gpus:<4}] {bar(share * len(nodes))}")
    footer()


def main():
    global PER_GPU, INTERACTIVE
    args = list(sys.argv[1:])
    PER_GPU = "--per-gpu" in args
    once = "--once" in args
    args = [a for a in args if a not in ("--per-gpu", "--once", "--watch")]
    interval = 2.0
    if "--interval" in args:
        i = args.index("--interval")
        args.pop(i)
        interval = float(args.pop(i))
    cfg_path = args[0] if args else DEFAULT_CFG
    if not os.path.exists(cfg_path):
        sys.exit(f"no cluster config at {cfg_path} — is a fleet running?")
    with open(cfg_path) as f:
        cfg = json.load(f)

    if once:
        render(cfg, scrape(cfg["servers"]), None, 0)
        return

    global INTERACTIVE
    INTERACTIVE = sys.stdin.isatty()
    prev, t_prev, rows, dt = None, None, None, 0
    try:
        with Keys() as keys:
            while True:
                rows = scrape(cfg["servers"])
                now = time.time()
                dt = now - t_prev if t_prev else 0
                while True:  # redraw without rescraping when a key toggles the view
                    print("\033[2J\033[H", end="")
                    render(cfg, rows, prev, dt)
                    sys.stdout.flush()
                    key = keys.wait(interval)
                    if key is None:
                        break
                    if key.lower() == "q":
                        return
                    if key.lower() == "a":
                        PER_GPU = not PER_GPU
                        continue
                    break
                prev = {(r["server"]["host"], r["server"]["port"]): r["metrics"] for r in rows}
                t_prev = now
    except KeyboardInterrupt:
        pass
    finally:
        print()


PER_GPU = False
INTERACTIVE = False

if __name__ == "__main__":
    main()
