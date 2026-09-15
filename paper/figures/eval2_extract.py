#!/usr/bin/env python3
"""Eval 2 -- automatic tracking and knowledge creation, per model.

One row per (model, mode). What the tracker WROTE DOWN while working
(observations) is set against what that work was turned INTO (skills, MCP
tools) and how many distinct subjects it was filed under (topics).

Observations are attributed by timestamp, not by counting the file. A reuse
run's store arrives carrying the observation log of every run that promoted
before it -- the nano reuse log opens with entries written by the gpt-5.4
fresh run two hours earlier -- so the file length credits a run with tracking
it inherited. Entries at or after the run's own `created_at` are the ones it
actually wrote.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
ARM = "claude-phronix"


def run_start(manifest: dict) -> float | None:
    stamp = manifest.get("created_at")
    if not stamp:
        return None
    return dt.datetime.fromisoformat(stamp).timestamp()


def tracking(store: Path, since: float | None) -> tuple[int, int, int]:
    """(entries written, distinct topics, entries whose attempt worked)."""
    log = store / "research" / "observations.jsonl"
    if not log.is_file():
        return 0, 0, 0
    entries = 0
    worked = 0
    topics: set[str] = set()
    for line in log.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        at = rec.get("at")
        if since is not None and (at is None or at < since):
            continue
        entries += 1
        worked += int(bool(rec.get("worked")))
        topic = (rec.get("topic") or "").strip()
        if topic:
            topics.add(topic)
    return entries, len(topics), worked


def learned(run: Path, rows: list[dict]) -> tuple[int, int]:
    """(skills created, MCP tool modules promoted) for one run."""
    skills = sum(
        1 for r in rows for s in r.get("skills_created", [])
        if s.startswith("skills/")
    )
    tools = {
        p for r in rows for p in r.get("promoted", [])
        if p.startswith("capabilities/tools/") and p.endswith(".py")
    }
    return skills, len(tools)


FIELDS = ["model", "mode", "run", "tasks", "skills_learned", "tools_learned",
          "entries_tracked", "topics", "entries_worked"]


def collect(runs: list[Path]) -> list[dict]:
    # Keyed by RUN as well as model and mode.
    #
    # `out[(model, mode)] = ...` kept whichever run came last, so fourteen runs
    # produced six rows and every cell reported n=1 -- the figure could not
    # show a spread because the extract had already thrown it away, silently.
    out: dict[tuple[str, str, str], dict] = {}
    for run in runs:
        report, results = run / "report.json", run / ARM / "results.jsonl"
        if not (report.is_file() and results.is_file()):
            continue
        manifest = json.loads(report.read_text()).get("manifest", {})
        rows = [json.loads(l) for l in results.read_text().splitlines() if l.strip()]
        model = manifest.get("model", "?").replace("svc-dldl-", "")
        mode = "fresh" if manifest.get("fresh") else "reuse"

        skills, tools = learned(run, rows)
        entries, topics, worked = tracking(
            run / ARM / "store" / ".phronix", run_start(manifest))

        out[(model, mode, run.name)] = {
            "model": model, "mode": mode, "run": run.name, "tasks": len(rows),
            "skills_learned": skills, "tools_learned": tools,
            "entries_tracked": entries, "topics": topics,
            "entries_worked": worked,
        }
    return [out[k] for k in sorted(out)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "eval2_tracking.csv")
    ap.add_argument("--runs", nargs="*", default=None)
    args = ap.parse_args()

    names = args.runs or sorted(p.name for p in (args.bench / "runs").iterdir() if p.is_dir())
    rows = collect([args.bench / "runs" / n for n in names])
    if not rows:
        raise SystemExit("no usable runs")

    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} rows")
    for r in rows:
        print(f"  {r['model']:14s} {r['mode']:5s} skills={r['skills_learned']:3d} "
              f"tools={r['tools_learned']:3d} entries={r['entries_tracked']:5d} "
              f"topics={r['topics']:3d}")


if __name__ == "__main__":
    main()
