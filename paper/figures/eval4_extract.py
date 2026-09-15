#!/usr/bin/env python3
"""Eval 4 -- token cost per attempt, decomposed by outcome.

Three groups per category:

* `bare`          -- every bare task. Bare has no memory, so its fresh and
                     reuse runs are the same experiment run twice; they are
                     pooled, which halves the noise on a small sample.
* `phronix-fresh` -- every phronix task in a fresh run.
* `phronix-reuse` -- reuse applying what was successfully learnt: tasks whose
                     own model solved them in the fresh run (leaving a skill),
                     and which the reuse run then solved on its FIRST attempt.
                     By construction this group has no failures -- it is the
                     case where the corpus simply supplied the answer. A task
                     nothing ever solved has no reuse to measure. There is no
                     bare equivalent; bare reuses nothing.

The measure is tokens per TASK, and bare is multiplied by `--extrapolate`.
Per attempt, bare looks cheap for a reason that flatters it: it takes exactly
one attempt and stops, whether or not it succeeded. The comparison the paper
makes is against a bare agent given the same retry budget, so bare's single
measured attempt is scaled to that budget. That assumption is the figure's
main soft spot and is recorded in `bare_multiplier`.

Each group's cost splits into a solved and a failed part that SUM correctly:
both are divided by the group's TASK count, so the two stack to the group's
overall tokens-per-task and each segment is that total's share. Stacking two
separately-averaged means would not add up to anything.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

BENCH = Path("/p/lustre3/haridev/phronix-bench")
PHRONIX, BARE = "claude-phronix", "claude-bare"

FIELDS = ["model", "run", "group", "category", "tasks", "attempts", "tokens_total",
          "tokens_per_task", "solved_tasks", "solved_per_task",
          "failed_tasks", "failed_per_task", "bare_multiplier"]


def category_of(instance: str) -> str:
    return instance.split("__")[0].replace("-", "/", 1)


def read(run: Path, arm: str) -> list[dict]:
    p = run / arm / "results.jsonl"
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def collect(runs: list[Path], extrapolate: int) -> list[dict]:
    # (model, run, group, category) -> per-outcome tokens and attempts.
    #
    # Model, because pooling a three-model sweep into one figure averages over
    # the very thing being compared. Run, because five repeats of a condition
    # have to stay five rows for a figure to show their spread; summed, the
    # variance is gone before the plotter ever sees it.
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

        rid = run.name
        for r in read(run, BARE):
            staged.append(("bare", model, rid, r))
        if mode == "fresh":
            skills = run / PHRONIX / "store" / ".phronix" / "capabilities" / "skills"
            have = {d.name for d in skills.iterdir()} if skills.is_dir() else set()
            for r in read(run, PHRONIX):
                staged.append(("phronix-fresh", model, rid, r))
                # Confirmed, not assumed: the solved task really did leave a
                # skill directory behind.
                if r.get("resolved") and r["instance_id"].replace("__", "-") in have:
                    eligible[model].add(r["instance_id"])
        else:
            for r in read(run, PHRONIX):
                # Reuse means the learnt solution was applied and worked
                # immediately. A retry is the corpus not having supplied the
                # answer, which is a different thing being measured.
                if r.get("resolved") and r.get("tries") == 1:
                    staged.append(("phronix-reuse", model, rid, r))

    # Eligibility is pooled over the model's fresh runs, not paired run to
    # run: with repeats, a task one fresh repeat solved left a skill that a
    # later reuse run could genuinely use, and pairing by run index would call
    # that ineligible on a scheduling detail.
    for group, model, rid, r in staged:
        if group == "phronix-reuse" and r["instance_id"] not in eligible[model]:
            continue
        cat = r.get("repo") or category_of(r["instance_id"])
        cell = acc[(model, rid, group, cat)]
        outcome = "solved" if r.get("resolved") else "failed"
        cell["tasks"] += 1
        cell[f"{outcome}_tasks"] += 1
        tries = max(int(r.get("tries") or 0), 1)
        tokens = int(r.get("tokens_total") or 0)
        cell["attempts"] += tries
        cell["tokens_total"] += tokens
        cell[f"{outcome}_tokens"] += tokens

    rows = []
    for (model, rid, group, cat), v in sorted(acc.items()):
        tasks = v["tasks"] or 1
        # Bare ran one attempt per task and stopped; scale it to the retry
        # budget the comparison assumes.
        mult = extrapolate if group == "bare" else 1
        rows.append({
            "model": model, "run": rid,
            "group": group, "category": cat, "tasks": v["tasks"],
            "attempts": v["attempts"],
            "tokens_total": v["tokens_total"] * mult,
            "tokens_per_task": round(v["tokens_total"] / tasks * mult, 1),
            "solved_tasks": v["solved_tasks"],
            # Same denominator for both parts, so they stack to the total.
            "solved_per_task": round(v["solved_tokens"] / tasks * mult, 1),
            "failed_tasks": v["failed_tasks"],
            "failed_per_task": round(v["failed_tokens"] / tasks * mult, 1),
            "bare_multiplier": mult if group == "bare" else "",
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
        tasks = sum(r["tasks"] for r in sel) or 1
        print(f"  {group:14s} tasks={tasks:3d} attempts={att:3d} "
              f"solved/task={sum(r['solved_per_task']*r['tasks'] for r in sel)/tasks:10,.0f} "
              f"failed/task={sum(r['failed_per_task']*r['tasks'] for r in sel)/tasks:10,.0f}")


if __name__ == "__main__":
    main()
