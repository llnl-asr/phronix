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
import re
import select
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

def _llm_root():
    """Where this fleet's data lives — from the env.sh sitting NEXT TO THIS FILE.

    These two scripts are pure python and never source env.sh, so a hardcoded
    default sent every corona-llm invocation looking for Tuolumne's logs and
    sessions. The sibling env.sh is the one thing that always identifies which
    cluster this copy belongs to (corona-llm symlinks the scripts but carries
    its own env.sh), so read the default out of it.
    """
    if os.environ.get("LLM_ROOT"):
        return os.environ["LLM_ROOT"]
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.sh")
    try:
        with open(env) as handle:
            found = re.search(r"^export LLM_ROOT=\$\{LLM_ROOT:-([^}]+)\}", handle.read(), re.M)
    except OSError:
        found = None
    return found.group(1) if found else "/p/lustre5/haridev/llm-tuolumne"


LLM_ROOT = _llm_root()
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

#: Running peak per rate, so a gauge has a ceiling to draw against.
#: There is no fixed maximum for a fleet's token rate — it depends on the
#: model, the batch and how many replicas are up — so the only honest scale
#: is the best this fleet has managed while the display has been watching.
PEAK = {"prompt": 0.0, "generate": 0.0}

#: Which stat groups are drawn, toggled by the key in the first column.
#
# The summary grew a line per question worth asking — session, rates, load,
# balance, lifetime — and all of them together is more than fits above the
# replica table on a normal window, so the table scrolls off and the display
# stops being a `top`. Grouping lets a watcher keep the two lines they are
# actually chasing and drop the rest, the same way the benchmark's top toggles
# its panels.
#
# All on by default: the reader who has not pressed anything should see what
# this has always shown.
GROUPS = {
    "s": ["session", True],
    "t": ["throughput", True],
    "l": ["load", True],
    "b": ["balance", True],
    "f": ["lifetime", True],
}


def showing(name):
    return any(g[0] == name and g[1] for g in GROUPS.values())


def toggle_group(key):
    """Flip one group. Returns True if *key* named a group."""
    if key in GROUPS:
        GROUPS[key][1] = not GROUPS[key][1]
        return True
    return False

# ---- colour ------------------------------------------------------------------
# The same convention the benchmark's top.sh uses, so the two displays can be
# read side by side without relearning what a colour means:
#
#   green   healthy, and doing work      red     down, or a fault to act on
#   yellow  a warning worth reading      dim     context, not a finding
#
# Off when stdout is not a terminal: escape codes in a log or a pipe are noise,
# and they break the column alignment anything parsing this would rely on.
COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


_stdout_print = print

#: Lines written since the frame began, so the footer can be put on the last
#: row rather than wherever the content happened to end.
_ROW = 0

#: Rows this frame may use, and whether it has already said it ran out.
#
# Without a cap the frame simply prints past the bottom of the window, the
# terminal scrolls, and the line that scrolls away is line 1 — the model, the
# gateway and the replica count, which is the one line you cannot reconstruct
# from anything below it. Dropping from the BOTTOM keeps the identity of the
# fleet and loses the tail of a table, which is the right way round.
_HEIGHT = 0
_TRUNCATED = False


def print(*args, **kwargs):                      # noqa: A001 - deliberate
    """`print`, with each line erasing whatever it overwrites.

    The live view repaints by homing the cursor and writing over the previous
    frame rather than clearing the screen, because clearing makes the whole
    display blink. Overwriting leaves the tail of any line that used to be
    longer, so every line ends with `\033[K`. Wrapping `print` once is what
    keeps that invariant true for the twenty-odd call sites that render a frame,
    including the ones added later.
    """
    global _ROW, _TRUNCATED
    end = kwargs.pop("end", "\n")
    if end == "\n":
        # One row is reserved for the footer, one for the "more" marker.
        if _HEIGHT and _ROW >= _HEIGHT - 2:
            if not _TRUNCATED:
                _TRUNCATED = True
                _ROW += 1
                _stdout_print(dim("  ... more than fits; close a group with its "
                                  "key, or use a taller window"),
                              end="\033[K\n" if COLOUR else "\n")
            return
        _ROW += 1
        if COLOUR:
            end = "\033[K\n"
    _stdout_print(*args, end=end, **kwargs)


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if COLOUR else text


def green(t):
    return paint(t, "32")


def red(t):
    return paint(t, "31;1")


def yellow(t):
    return paint(t, "33")


def dim(t):
    return paint(t, "2")


def heat(text, frac):
    """Colour a replica by whether it is actually working.

    Idle replicas are what this display exists to surface: a fleet can be
    perfectly healthy and still have three quarters of its GPUs doing nothing,
    and in plain text that reads exactly like a fleet that is busy.
    """
    if frac <= 0:
        return dim(text)
    return green(text) if frac > 0.02 else yellow(text)


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
    if not servers:
        return []
    with ThreadPoolExecutor(max_workers=min(64, len(servers))) as ex:
        return list(ex.map(fetch, servers))


# ---- following the fleet that is actually up ---------------------------------
# The config on disk is a snapshot taken when a deploy FINISHED, and a fleet is
# most interesting before that: `deploy.sh` writes cluster.json last, so while
# the servers are loading their weights the in-repo copy still describes the
# previous fleet — or, if the deploy wrote its placeholder first, describes this
# one with an empty `servers` list (which used to crash this display outright:
# "max_workers must be greater than 0").
#
# So: take the NEWEST config of the ones written, and fill in `servers` from the
# per-GPU records `gpu-server.sh` drops in <run_dir>/nodes as each replica comes
# up. That directory is the fleet's real membership, live, and it is what makes
# `status.sh` show a cluster mid-launch instead of the last one.
def newest_cfg_path(explicit=None):
    if explicit:
        return explicit
    cands = [REPO_CFG, os.path.join(LLM_ROOT, "logs", "cluster.json")]
    cands = [c for c in cands if os.path.exists(c)]
    if not cands:
        return None
    return max(cands, key=lambda c: _run_stamp(c))


def _run_stamp(path):
    """A config's age, by its run directory rather than its own mtime.

    The in-repo copy is written by `cp`, so its mtime is the copy's; the run
    directory's name is the deploy's own timestamp and is what actually orders
    two fleets.
    """
    try:
        with open(path) as f:
            rd = json.load(f).get("run_dir", "")
        return (os.path.basename(rd), os.path.getmtime(path))
    except Exception:
        return ("", 0.0)


def load_cfg(path):
    with open(path) as f:
        cfg = json.load(f)
    servers = [s for s in cfg.get("servers") or [] if s]
    if not servers:
        servers = read_node_records(cfg.get("run_dir", ""))
    cfg["servers"] = servers
    return cfg


def read_node_records(run_dir):
    d = os.path.join(run_dir, "nodes")
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, name)) as f:
                out.append(json.load(f))
        except Exception:
            continue  # being written right now; it will be there next refresh
    return out


def fairness(values):
    """Jain's fairness index: 1.0 = perfectly even, 1/n = one replica does it all."""
    n, s, sq = len(values), sum(values), sum(v * v for v in values)
    return (s * s) / (n * sq) if n and sq else 1.0


def verdict(fi):
    if fi >= 0.95:
        return green("balanced")
    return yellow("slightly uneven") if fi >= 0.85 else red("IMBALANCED")


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


# ---- the open session, if there is one ---------------------------------------
# Everything above is "since the fleet booted" or "in the last interval". A
# session is the third question — what has happened since a benchmark said
# start — and it is the one worth reading while a benchmark is running, so it
# goes at the top of the display whenever a session is open. The per-replica
# table is dropped: this display already has one.
#
# Cached, because building it is not free: an open session has no end snapshot
# on disk, so the report takes a LIVE one — every replica's /metrics and /slots
# again, on top of the scrape this display just did. At a 2s refresh that
# doubled the per-cycle network work and made the whole view stutter. The
# session window is minutes long; recomputing it every ten seconds loses
# nothing a human could see.
_SESSION_CACHE = {"at": 0.0, "lines": []}
_SESSION_TTL = 10.0


def finished_sessions(cfg, limit=3):
    """The sessions this fleet has already served, newest first.

    `session_lines` shows the OPEN session and nothing else, so the moment a
    benchmark closed its window the fleet's whole measured history vanished from
    this screen — the numbers were on disk and invisible. `session.sh stop` now
    copies each finished session into the run directory beside the gateway and
    per-GPU logs, which is what makes them findable from here.
    """
    run_dir = (cfg or {}).get("run_dir") or ""
    folder = os.path.join(run_dir, "sessions")
    if not run_dir or not os.path.isdir(folder):
        return []
    out = []
    try:
        names = sorted(os.listdir(folder), reverse=True)
    except OSError:
        return []
    for name in names:
        path = os.path.join(folder, name, "report.txt")
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as handle:
                head = handle.readline().strip()
        except OSError:
            continue
        # The report's first line already names the session and its window;
        # anything more belongs in the file, which this points at.
        out.append(dim(f"  past  {head[:150]}"))
        if len(out) >= limit:
            break
    if out:
        out.insert(0, dim(f"  {len(out)} finished session(s) in {folder}"))
    return out


def session_lines():
    link = os.path.join(LLM_ROOT, "logs", "sessions", "current")
    if not os.path.exists(link):
        return []
    now = time.time()
    if now - _SESSION_CACHE["at"] < _SESSION_TTL:
        return _SESSION_CACHE["lines"]
    try:
        import importlib.machinery
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.sh")
        loader = importlib.machinery.SourceFileLoader("phronix_session", path)
        spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        text = mod.report(os.path.realpath(link))
    except Exception as e:
        return [dim(f"  session     unreadable ({e})")]
    out = []
    for line in text.splitlines():
        if line.strip().startswith("REPLICA"):
            break
        out.append(line)
    lines = [l for l in out if l.strip()]
    _SESSION_CACHE.update(at=now, lines=lines)
    return lines


def footer():
    """Pin the key legend to the bottom row, and never scroll the terminal.

    Two bugs, one cause. The legend used to be printed wherever the content
    happened to end, with a trailing newline — and when the frame filled the
    window that newline scrolled everything up by one line. `\033[H` then homed
    to a display shifted out from under it, so the previous frame's legend
    survived below the new one and the whole view looked doubled.

    So: pad to the last row with blank lines that erase what they land on, and
    write the legend with NO trailing newline. Nothing is ever printed past the
    bottom-right cell, so the terminal has no reason to scroll and the frame
    stays registered with `\033[H` from one refresh to the next.
    """
    if not INTERACTIVE:
        return
    # Named with their state, so the footer says what is ON as well as what the
    # key does — a toggle whose current setting is invisible reads as broken.
    marks = " ".join(f"[{k}]{name}{'*' if on else ''}"
                     for k, (name, on) in GROUPS.items())
    text = (f"\033[2m{marks}   "
            f"[a] {'aggregated view' if PER_GPU else 'all replicas'}   "
            f"[q] quit\033[0m")
    height = shutil.get_terminal_size((80, 24)).lines
    while _ROW < height - 1:
        print("")
    _stdout_print(("\033[K" if COLOUR else "") + text, end="", flush=True)


def render(cfg, rows, prev, dt):
    global _ROW, _HEIGHT, _TRUNCATED
    _ROW = 0
    _TRUNCATED = False
    # Only bound the frame on a terminal. Piped output has no height and
    # truncating it would silently shorten a report someone is parsing.
    _HEIGHT = shutil.get_terminal_size((80, 24)).lines if COLOUR else 0
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
    alive = gateway_ok(gw)
    # The gateway is the single point everything else depends on: with it down
    # every replica below can be perfectly healthy and nothing can reach them.
    print(f"\033[1m{cfg['alias']}\033[0m  profile {cfg.get('profile', '?')}  "
          f"gateway {gw['host']}:{gw['port']} "
          f"[{green('UP') if alive else red('DOWN')}]  "
          f"replicas {(green if up == len(rows) else red)(f'{up}/{len(rows)}')}  "
          f"{'live, last %.1fs' % dt if live else 'cumulative since start'}")
    if showing("session"):
        for line in session_lines():
            print(line)
        # What this fleet has already measured, not only what it is measuring.
        for line in finished_sessions(cfg):
            print(line)
    # One shape for every stat line, the way `top` writes its summary block:
    # a dim label in a fixed column, then the value, then a gauge where there is
    # a ceiling worth seeing. Before this each line invented its own spacing and
    # its own units, so nothing lined up vertically and the eye had to re-find
    # the number on every row.
    def stat(label, body, gauge=None):
        bars = f"  {dim(gauge)}" if gauge else ""
        print(f"  {dim(f'{label:<11}')} {body}{bars}")

    if live and showing("throughput"):
        busy = sum(r["metrics"].get("n_busy_slots_per_decode", 0) for r in rows)
        pr = tot["prompt_tokens_total"] / window
        gn = tot["tokens_predicted_total"] / window
        # Prompt and generate are on wildly different scales — a 13:1 ratio is
        # normal — so a shared axis would leave the generate bar always empty.
        # Each is drawn against its own running peak instead, which is what
        # makes a stall visible: the bar falls even though the number is large.
        PEAK["prompt"] = max(PEAK["prompt"], pr)
        PEAK["generate"] = max(PEAK["generate"], gn)
        stat("throughput",
             f"prompt {green(f'{pr:8.0f}')} tok/s   "
             f"generate {green(f'{gn:8.0f}')} tok/s   "
             f"total {pr + gn:8.0f} tok/s",
             bar(pr / PEAK["prompt"] if PEAK["prompt"] else 0))
        # Busy slots against the fleet's capacity, which is the ceiling that
        # actually exists: replicas x slots each.
        slots = max(1, len(rows))
        stat("activity",
             f"{tot['n_decode_total'] / window:8.0f} decode it/s   "
             f"{heat(f'{busy:.1f}', busy / slots)} slot(s) busy of {slots} replica(s)",
             bar(busy / slots))
    elif showing("throughput"):
        stat("totals",
             f"prompt {tot['prompt_tokens_total']:9.0f}   "
             f"generate {tot['tokens_predicted_total']:9.0f}   "
             f"total {tot['prompt_tokens_total'] + tot['tokens_predicted_total']:9.0f} tokens")
    # Active replicas coloured against the fleet size: this is the number that
    # answers "is the run big enough to fill what is deployed".
    share_active = active / max(1, len(rows))
    if showing("load"):
        stat("load",
         f"{int(inflight):4d} in flight   "
         f"{(yellow if deferred else dim)(f'{int(deferred):4d}')} deferred   "
             f"{heat(f'{active}/{len(rows)}', share_active)} replica(s) active"
             + (dim("   most of the fleet is idle") if share_active < 0.5 else ""),
             bar(share_active))
    # With only a handful of requests left in flight a low fairness score says
    # nothing useful, so do not cry imbalance over a draining queue.
    if not showing("balance"):
        pass
    elif inflight < len(rows) and active < len(rows) / 2:
        stat("balance", dim(f"too little load to judge — {int(inflight)} in "
                            f"flight across {len(rows)} replicas"))
    else:
        note = "" if inflight >= 2 * len(rows) else dim(
            f"   light load: {int(inflight)} in flight, discount this")
        stat("balance",
             f"work {work_fi:.3f} ({verdict(work_fi)})   "
             f"requests {req_fi:.3f} ({verdict(req_fi)})   "
             + dim(f"share of {'decode work' if live else 'generated tokens'}")
             + note,
             bar(work_fi))
    if showing("lifetime"):
        stat("lifetime", f"{human(cum_p + cum_g)} tokens   "
                         + dim(f"{human(cum_p)} prompt + {human(cum_g)} generated"))
    drafted = tot["spec_decode_num_draft_tokens_total"]
    if drafted and showing("lifetime"):
        accepted = tot["spec_decode_num_accepted_tokens_total"] / drafted
        stat("speculative",
             f"{green(f'{accepted * 100:.1f}%')} of {int(drafted)} drafted "
             f"tokens accepted", bar(accepted))
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
                  f"{green('   up') if row['up'] else red(' DOWN')}"
                  f"{int(m.get('requests_processing', 0)):>5}{int(m.get('requests_deferred', 0)):>5}"
                  f"{d['prompt_tokens_total'] / window:>9.0f}"
                  f"{d['tokens_predicted_total'] / window:>9.0f}"
                  f"{d['n_decode_total'] / window:>9.0f}"
                  f"{heat(f'{share * 100:>7.1f}%', share)}  "
                  f"{heat(bar(share * len(per)), share)}")
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
        healthy = n["up"] == len(n["gpus"])
        alive = f"{n['up']:>3}/{len(n['gpus']):<1}"
        print(f"{host:<14}"
              f"{(green if healthy else red)(alive)}"
              f"{int(n['run']):>5}{int(n['def']):>5}"
              f"{n['pp'] / window:>10.0f}{n['tg'] / window:>10.0f}{n['dec'] / window:>9.0f}"
              f"{heat(f'{share * 100:>7.1f}%', share)}  "
              f"[{heat(f'{gpus:<4}', share)}] {heat(bar(share * len(nodes)), share)}")
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
    cfg_path = newest_cfg_path(args[0] if args else None)
    if not cfg_path or not os.path.exists(cfg_path):
        sys.exit("no cluster config found — is a fleet running?")
    cfg = load_cfg(cfg_path)

    if once:
        render(cfg, scrape(cfg["servers"]), None, 0)
        return

    global INTERACTIVE
    INTERACTIVE = sys.stdin.isatty()
    prev, t_prev, rows, dt = None, None, None, 0
    try:
        with Keys() as keys:
            while True:
                # Re-read every cycle: a deploy launched while this is open
                # should appear here, and replicas should appear as they come
                # up rather than at the end.
                cfg_path = newest_cfg_path(args[0] if args else None) or cfg_path
                try:
                    cfg = load_cfg(cfg_path)
                except Exception:
                    pass  # mid-write; keep the last good one
                rows = scrape(cfg["servers"])
                now = time.time()
                dt = now - t_prev if t_prev else 0
                while True:  # redraw without rescraping when a key toggles the view
                    # Home the cursor and overwrite; do NOT clear the screen.
                    #
                    # `\033[2J` blanks every cell and the redraw fills it back
                    # in, so on a remote terminal the empty state is visible and
                    # the whole view blinks twice a second — for a display where
                    # most of the frame is identical to the last one. Overwriting
                    # in place leaves nothing to flash: each line erases its own
                    # tail as it is written (see `print` above), and `\033[J`
                    # after the frame clears whatever the shorter new frame did
                    # not reach.
                    print("\033[H", end="")
                    render(cfg, rows, prev, dt)
                    print("\033[J", end="", flush=True)
                    sys.stdout.flush()
                    key = keys.wait(interval)
                    if key is None:
                        break
                    if key.lower() == "q":
                        return
                    if key.lower() == "a":
                        PER_GPU = not PER_GPU
                        continue
                    # A group toggle redraws from the SAME scrape rather than
                    # falling through to a rescrape: the numbers did not change,
                    # only which of them are drawn, and waiting a full interval
                    # to see the effect of a keypress reads as a dropped key.
                    if toggle_group(key.lower()):
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
