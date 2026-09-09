#!/usr/bin/env python3
"""Eval 4 -- end-to-end token cost per attempt, fresh and reuse.

One row per (mode, arm, category, outcome). The measure is tokens per ATTEMPT,
not per task: phronix retries and bare does not, so per-task totals compare a
budget against a single shot. Per attempt asks the fairer question -- what does
one swing of the bat cost each of them?

Bare's `tries` is always 1, so its per-attempt figure IS its per-task figure.
The five-attempt extrapolation is carried in `est_total_5` for the cost
argument; it does not change the per-attempt number, which is what the figure
plots.

Split by outcome because a failed attempt is not a cheap success: it is a full
budget spent reaching nothing, and averaging the two hides which one the
tokens went to.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
ARMS = {"claude-bare": "bare", "claude-phronix": "phronix"}

FIELDS = ["mode", "arm", "category", "outcome", "tasks", "attempts",
          "tokens_total", "tokens_per_try", "est_total_5"]


def category_of(instance: str) -> str:
    return instance.split("__")[0].replace("-", "/", 1)


def collect(runs: list[Path], extrapolate: int) -> list[dict]:
    acc: dict[tuple, dict] = defaultdict(
        lambda: {"tasks": 0, "attempts": 0, "tokens_total": 0})

    for run in runs:
        report = run / "report.json"
        if not report.is_file():
            continue
        manifest = json.loads(report.read_text()).get("manifest", {})
        mode = "fresh" if manifest.get("fresh") else "reuse"

        for arm_dir, arm in ARMS.items():
            results = run / arm_dir / "results.jsonl"
            if not results.is_file():
                continue
            for line in results.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                cat = r.get("repo") or category_of(r["instance_id"])
                outcome = "solved" if r.get("resolved") else "failed"
                cell = acc[(mode, arm, cat, outcome)]
                cell["tasks"] += 1
                # Guard the divisor: a task that recorded no attempt still
                # burned tokens, and dividing by zero would drop it silently.
                cell["attempts"] += max(int(r.get("tries") or 0), 1)
                cell["tokens_total"] += int(r.get("tokens_total") or 0)

    rows = []
    for (mode, arm, cat, outcome), v in sorted(acc.items()):
        per_try = v["tokens_total"] / v["attempts"] if v["attempts"] else 0
        rows.append({
            "mode": mode, "arm": arm, "category": cat, "outcome": outcome,
            "tasks": v["tasks"], "attempts": v["attempts"],
            "tokens_total": v["tokens_total"],
            "tokens_per_try": round(per_try, 1),
            # What bare would cost if it were given the same retry budget
            # phronix uses. An assumption, kept beside the measurement.
            "est_total_5": round(per_try * extrapolate, 1) if arm == "bare" else "",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--extrapolate", type=int, default=5,
                    help="attempt budget assumed for the bare arm")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "eval4_tokens.csv")
    ap.add_argument("--runs", nargs="*", default=None)
    args = ap.parse_args()

    names = args.runs or sorted(p.name for p in (args.bench / "runs").iterdir() if p.is_dir())
    rows = collect([args.bench / "runs" / n for n in names], args.extrapolate)
    if not rows:
        raise SystemExit("no usable runs")

    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} rows")
    for mode in ("fresh", "reuse"):
        for arm in ("bare", "phronix"):
            for outcome in ("solved", "failed"):
                sel = [r for r in rows if r["mode"] == mode and r["arm"] == arm
                       and r["outcome"] == outcome]
                if not sel:
                    continue
                tok = sum(r["tokens_total"] for r in sel)
                att = sum(r["attempts"] for r in sel)
                print(f"  {mode:5s} {arm:7s} {outcome:6s} tasks={sum(r['tasks'] for r in sel):3d} "
                      f"attempts={att:3d} tokens/try={tok/att:,.0f}")


if __name__ == "__main__":
    main()
