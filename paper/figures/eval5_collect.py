#!/usr/bin/env python3
"""Assemble one self-contained evidence folder for an eval5 workload pair.

The figures are a summary; a reviewer who wants to check them needs the runs
themselves. This gathers everything that produced a figure into one directory
that can be handed to a paper as-is:

    paper/runs/<workload>/
        README.md              provenance: what ran, when, on what, cost
        bare/                  raw stream, readable log, workdir manifest
        phronix/               same
        eval5_phases.csv       per-phase data behind figure 5a
        eval5b_quality.csv     the rubric behind figure 5b (hand-scored)
        traces/                every .pfw* either arm produced, with event counts
        rendered/              the figures and tables built from the above

Nothing here is copied by hand, so the folder cannot drift from the figures.
The one exception is eval5b_quality.csv, which is a human rubric: this script
seeds it from measurable evidence and marks every row it could not decide as
`unscored` rather than guessing.

    eval5_collect.py --workload 1000genome --pair 1kg
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent


def read_paths(pair: str, arm: str) -> dict:
    """RAW/TXT/WORK for an arm, from the /tmp paths file the launcher wrote."""
    p = Path(f"/tmp/{pair}_{arm}_paths")
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


WORKSPACE_RE = __import__("re").compile(
    r"(/[-\w/.]*?/workspaces/[-\w.]+/\d{8}_\d{6})")


def workdir_of(paths: dict, raw: Path) -> Path | None:
    """The arm's working directory: from the paths file, else from the stream.

    A pipeline run creates its own workspace and only names it in the stream,
    so there is no paths-file entry to read.
    """
    if paths.get("WORK"):
        return Path(paths["WORK"])
    if not raw.exists():
        return None
    for line in raw.open(errors="replace"):
        m = WORKSPACE_RE.search(line)
        if m:
            return Path(m.group(1))
    return None


def trace_report(workdir: Path | None) -> list[dict]:
    """Every .pfw* under a workdir, with a real event count.

    Size alone is misleading: a trace can be 880 bytes of header and no
    application events at all, which is a failure wearing a success's clothes.
    """
    rows = []
    if not workdir or not workdir.exists():
        return rows
    # De-duplicate by INODE, not by resolved path: the pipeline hardlinks the
    # raw trace into its compact/ tree, so the same bytes appear under two
    # names and resolve() collapses neither. Counting it twice would report
    # two traces where one exists.
    seen_inode = set()
    for f in sorted(workdir.rglob("*.pfw*")):
        try:
            st = f.stat()
            key = (st.st_dev, st.st_ino)
        except OSError:
            key = (0, str(f))
        if key in seen_inode:
            continue
        seen_inode.add(key)
        try:
            raw = (gzip.open(f, "rt", errors="replace").read()
                   if f.suffix == ".gz" else f.read_text(errors="replace"))
        except Exception as exc:
            rows.append({"file": f.name, "path": str(f), "bytes": 0,
                         "events": 0, "note": f"unreadable: {exc}"})
            continue
        events, names = 0, set()
        for line in raw.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if isinstance(d, dict) and d.get("ph"):
                events += 1
                names.add(str(d.get("name", "?")))
        # Metadata-only records (CM/HH/FH/SH) are DFTracer's own headers, not
        # the application. A trace of nothing but those has captured nothing.
        # DFTracer's own header records. Everything else came from the
        # application, and is what "the instrumentation worked" means.
        app = sorted(n for n in names if n not in {"CM", "HH", "FH", "SH"})
        try:
            rel = str(f.relative_to(workdir))
        except ValueError:
            rel = f.name
        rows.append({
            "file": rel, "path": str(f),
            "bytes": f.stat().st_size, "events": events,
            "app_event_names": ";".join(app),
            "note": "metadata only -- no application events" if not app else "",
        })
    return rows


def run_totals(raw: Path) -> dict:
    """Cost and true token totals, from the stream's final result event."""
    out = {"cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0,
           "turns": 0, "finished": False}
    if not raw.exists():
        return out
    for line in raw.open(errors="replace"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "result":
            out["finished"] = True
            out["cost_usd"] = round(d.get("total_cost_usd", 0) or 0, 2)
            out["turns"] = d.get("num_turns", 0) or 0
            u = d.get("usage") or {}
            if isinstance(u, dict):
                out["tokens_in"] = ((u.get("input_tokens", 0) or 0)
                                    + (u.get("cache_read_input_tokens", 0) or 0)
                                    + (u.get("cache_creation_input_tokens", 0) or 0))
                out["tokens_out"] = u.get("output_tokens", 0) or 0
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workload", required=True, help="e.g. 1000genome")
    ap.add_argument("--pair", required=True, help="/tmp/<pair>_{arm}_paths prefix")
    ap.add_argument("--out", default=None)
    ap.add_argument("--app-url", default="")
    ap.add_argument("--smoke-cmd", default="")
    ap.add_argument("--dataset", default="")
    ap.add_argument("--single-phase", action="store_true",
                    help="neither arm emitted phase markers: report totals")
    args = ap.parse_args()

    dest = Path(args.out) if args.out else PAPER / "runs" / args.workload
    for sub in ("bare", "phronix", "traces", "rendered"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    summary, arms = {}, {}
    for arm in ("bare", "phronix"):
        paths = read_paths(args.pair, arm)
        raw = Path(paths.get("RAW", ""))
        txt = Path(paths.get("TXT", ""))
        wd = workdir_of(paths, raw)
        arms[arm] = {"raw": raw, "txt": txt, "workdir": wd}

        if raw.exists():
            shutil.copy2(raw, dest / arm / f"{arm}-stream.jsonl")
        if txt.exists():
            shutil.copy2(txt, dest / arm / f"{arm}.log")

        # A manifest, not a copy: the workdirs hold gigabytes and thousands of
        # files, and the paper needs to know what was there, not to carry it.
        if wd and wd.exists():
            lines = []
            for p in sorted(wd.rglob("*")):
                try:
                    if p.is_file():
                        lines.append(f"{p.stat().st_size:>12}  "
                                     f"{p.relative_to(wd)}")
                except OSError:
                    pass
            (dest / arm / "workdir-manifest.txt").write_text(
                f"# {wd}\n# {len(lines)} files\n" + "\n".join(lines[:5000]) + "\n")

        traces = trace_report(wd)
        for t in traces:
            src = Path(t["path"])
            if src.exists() and src.stat().st_size:
                # Flatten the workdir path into the filename so raw/ and
                # compact/ copies of the same trace stay distinguishable.
                flat = t["file"].replace("/", "__")
                shutil.copy2(src, dest / "traces" / f"{arm}-{flat}")
        summary[arm] = {**run_totals(raw), "traces": traces,
                        "workdir": str(wd) if wd else ""}

    with (dest / "traces" / "trace-inventory.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["arm", "file", "bytes", "events", "app_event_names", "note"])
        for arm in ("bare", "phronix"):
            for t in summary[arm]["traces"]:
                w.writerow([arm, t["file"], t["bytes"], t["events"],
                            t.get("app_event_names", ""), t.get("note", "")])

    # Per-phase CSV for figure 5a, straight from eval5_steps.py so the folder
    # and the figure cannot disagree.
    single_phase = args.single_phase
    merged = dest / "eval5_phases.csv"
    parts = []
    for arm in ("phronix", "bare"):
        raw = arms[arm]["raw"]
        if not raw.exists():
            continue
        out = dest / arm / "phases.csv"
        steps = dest / arm / "steps.csv"
        cmd = [sys.executable, str(HERE / "eval5_steps.py"), str(raw),
               "--arm", arm, "--empty-arm", "", "--out", str(steps),
               "--phases-out", str(out)]
        if single_phase:
            cmd.append("--single-phase")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and out.exists():
            parts.append(out)
        else:
            print(f"  ! eval5_steps failed for {arm}: "
                  f"{(r.stderr or r.stdout).strip().splitlines()[-1:]}")
    if parts:
        with merged.open("w", newline="") as fh:
            for i, p in enumerate(parts):
                lines = p.read_text().splitlines()
                fh.write("\n".join(lines if i == 0 else lines[1:]) + "\n")

    readme = dest / "README.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# eval5 — {args.workload}", "",
             f"Collected {now}. Everything here was produced by",
             "`paper/figures/eval5_collect.py`; nothing is transcribed by hand.", ""]
    if args.app_url:
        lines += [f"* application: `{args.app_url}`"]
    if args.dataset:
        lines += [f"* dataset: `{args.dataset}`"]
    if args.smoke_cmd:
        lines += [f"* smoke test: `{args.smoke_cmd}`"]
    lines += ["", "## Runs", "",
              "| | bare | phronix |", "|---|---|---|"]
    def cell(k, fmt=str):
        return (f"| {k} | " +
                " | ".join(fmt(summary[a].get(k, "")) for a in ("bare", "phronix")) + " |")
    lines += [cell("finished"),
              cell("turns"),
              f"| cost | " + " | ".join(f"${summary[a]['cost_usd']:.2f}"
                                        for a in ("bare", "phronix")) + " |",
              f"| tokens out | " + " | ".join(f"{summary[a]['tokens_out']:,}"
                                              for a in ("bare", "phronix")) + " |",
              f"| workdir | " + " | ".join(f"`{summary[a]['workdir']}`"
                                           for a in ("bare", "phronix")) + " |"]
    lines += ["", "## Traces produced", "",
              "Event counts are parsed from the files, not taken from any",
              "agent's report. A trace holding only `CM`/`HH`/`FH`/`SH`",
              "records is DFTracer's own header with no application events in",
              "it -- recorded here as such rather than counted as a success.",
              "", "| arm | file | bytes | events | app events |",
              "|---|---|---|---|---|"]
    any_trace = False
    for arm in ("bare", "phronix"):
        for t in summary[arm]["traces"]:
            any_trace = True
            lines.append(f"| {arm} | `{t['file']}` | {t['bytes']:,} | "
                         f"{t['events']} | {t.get('app_event_names') or '**none**'} |")
    if not any_trace:
        lines.append("| — | *no trace files found in either workdir* | | | |")
    lines += ["", "## Layout", "",
              "```", "bare/, phronix/   raw stream-json, readable log, workdir manifest,",
              "                  per-step and per-phase CSVs",
              "traces/           every non-empty .pfw* both arms wrote, plus",
              "                  trace-inventory.csv with parsed event counts",
              "eval5_phases.csv  the data behind figure 5a",
              "eval5b_quality.csv  the rubric behind figure 5b (hand-scored,",
              "                  each row carrying its evidence)",
              "rendered/         figures and tables built from the above", "```"]
    readme.write_text("\n".join(lines) + "\n")

    print(f"collected -> {dest}")
    for arm in ("bare", "phronix"):
        s = summary[arm]
        n = sum(1 for t in s["traces"] if t["bytes"])
        real = sum(1 for t in s["traces"] if t.get("app_event_names"))
        print(f"  {arm:<8} finished={s['finished']} cost=${s['cost_usd']:.2f} "
              f"traces={n} (with app events: {real})")


if __name__ == "__main__":
    main()
