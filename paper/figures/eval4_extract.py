#!/usr/bin/env python3
"""Eval 4 -- token cost per attempt, decomposed by outcome.

Three groups per category:

* `bare`          -- every bare task. Bare has no memory, so its fresh and
                     reuse runs are the same experiment run twice; they are
                     pooled, which halves the noise on a small sample.
* `phronix-fresh` -- every phronix task in a fresh run.
* `phronix-reuse` -- ONLY the tasks a reuse run could actually reuse
                     something for: those its own model solved in the fresh
                     run, and so left a skill behind. A task nothing ever
                     solved has no reuse to measure, and including it would
                     charge the reuse arm for work the corpus never covered.
                     There is no bare equivalent -- bare reuses nothing.

Each group's cost splits into a solved and a failed part that SUM correctly:
both are divided by the group's total attempts, so the two stack to the
group's overall tokens-per-attempt and each segment is that total's share.
Stacking two separately-averaged means would not add up to anything.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
PHRONIX, BARE = "claude-phronix", "claude-bare"

FIELDS = ["group", "category", "tasks", "attempts", "tokens_total",
          "tokens_per_try", "solved_tasks", "solved_per_try",
          "failed_tasks", "failed_per_try", "est_total_5"]


def category_of(instance: str) -> str:
    return instance.split("__")[0].replace("-", "/", 1)


def read(run: Path, arm: str) -> list[dict]:
    p = run / arm / "results.jsonl"
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def collect(runs: list[Path], extrapolate: int) -> list[dict]:
    # (group, category) -> per-outcome tokens and attempts
    acc: dict[tuple, dict] = defaultdict(lambda: defaultdict(int))
    # model -> tasks its FRESH run solved, which is what makes a reuse task
    # eligible.
    eligible: dict[str, set[str]] = defaultdict(set)
    staged: list[tuple] = []

    for run in runs:
        report = run / "report.json"
        if not report.is_file():
            continue
        manifest = json.loads(report.read_text()).get("manifest", {})
        mode = "fresh" if manifest.get("fresh") else "reuse"
        model = manifest.get("model", "?").replace("svc-dldl-", "")

        for r in read(run, BARE):
            staged.append(("bare", None, r))
        if mode == "fresh":
            skills = run / PHRONIX / "store" / ".phronix" / "capabilities" / "skills"
            have = {d.name for d in skills.iterdir()} if skills.is_dir() else set()
            for r in read(run, PHRONIX):
                staged.append(("phronix-fresh", None, r))
                # Confirmed, not assumed: the solved task really did leave a
                # skill directory behind.
                if r.get("resolved") and r["instance_id"].replace("__", "-") in have:
                    eligible[model].add(r["instance_id"])
        else:
            for r in read(run, PHRONIX):
                staged.append(("phronix-reuse", model, r))

    for group, model, r in staged:
        if group == "phronix-reuse" and r["instance_id"] not in eligible[model]:
            continue
        cat = r.get("repo") or category_of(r["instance_id"])
        cell = acc[(group, cat)]
        outcome = "solved" if r.get("resolved") else "failed"
        cell["tasks"] += 1
        cell[f"{outcome}_tasks"] += 1
        tries = max(int(r.get("tries") or 0), 1)
        tokens = int(r.get("tokens_total") or 0)
        cell["attempts"] += tries
        cell["tokens_total"] += tokens
        cell[f"{outcome}_tokens"] += tokens

    rows = []
    for (group, cat), v in sorted(acc.items()):
        att = v["attempts"] or 1
        rows.append({
            "group": group, "category": cat, "tasks": v["tasks"],
            "attempts": v["attempts"], "tokens_total": v["tokens_total"],
            "tokens_per_try": round(v["tokens_total"] / att, 1),
            "solved_tasks": v["solved_tasks"],
            # Same denominator for both parts, so they stack to the total.
            "solved_per_try": round(v["solved_tokens"] / att, 1),
            "failed_tasks": v["failed_tasks"],
            "failed_per_try": round(v["failed_tokens"] / att, 1),
            "est_total_5": round(v["tokens_total"] / att * extrapolate, 1)
            if group == "bare" else "",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--extrapolate", type=int, default=5)
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
    for group in ("bare", "phronix-fresh", "phronix-reuse"):
        sel = [r for r in rows if r["group"] == group]
        att = sum(r["attempts"] for r in sel) or 1
        print(f"  {group:14s} tasks={sum(r['tasks'] for r in sel):3d} "
              f"attempts={att:3d} "
              f"solved/try={sum(r['solved_per_try']*r['attempts'] for r in sel)/att:9,.0f} "
              f"failed/try={sum(r['failed_per_try']*r['attempts'] for r in sel)/att:9,.0f}")


if __name__ == "__main__":
    main()
