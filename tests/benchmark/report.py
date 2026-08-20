"""Turn a run directory into tables a person can argue with.

The report leads with the comparison verdict rather than the resolve rates,
because the resolve rates on 30 tasks are not the interesting part — the question
is whether accumulating skills changed anything, and that is a *difference*
between arms, with an interval attached.

Two presentational rules, both about not overstating:

* Every slope is printed with its 95% interval. A slope quoted bare on this
  sample size will be repeated as if it were precise.
* Any arm whose token counts were scraped rather than measured is marked. The
  phronix arms get exact figures from their own collector; the others are parsed
  out of stdout, and presenting the two as equally solid would be misleading.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .arms import ARM_ORDER
from .metrics import TaskResult, compare, read_results, summarise_arm


def load_run(run_dir: Path) -> Dict[str, List[TaskResult]]:
    run_dir = Path(run_dir)
    out: Dict[str, List[TaskResult]] = {}
    for arm_dir in sorted(run_dir.iterdir()):
        results = arm_dir / "results.jsonl"
        if arm_dir.is_dir() and results.is_file():
            out[arm_dir.name] = read_results(results)
    return out


def build(run_dir: Path, window: int = 10) -> Dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}

    results = load_run(run_dir)
    summaries = {arm: summarise_arm(rows, window=window) for arm, rows in results.items()}
    return {
        "run": str(run_dir),
        "manifest": manifest,
        "summaries": summaries,
        "comparison": compare(summaries),
    }


def _fmt_slope(value: float, ci: Optional[List[float]] = None) -> str:
    text = f"{value:+.4f}"
    if ci and all(abs(v) != float("inf") for v in ci):
        text += f" [{ci[0]:+.4f}, {ci[1]:+.4f}]"
    return text


def render(report: Dict[str, Any]) -> str:
    manifest = report.get("manifest", {})
    summaries: Dict[str, Any] = report.get("summaries", {})
    ordered = [a for a in ARM_ORDER if a in summaries] + \
              [a for a in summaries if a not in ARM_ORDER]

    lines: List[str] = [
        f"# Benchmark — {Path(report['run']).name}",
        "",
        f"model `{manifest.get('provider', '?')}/{manifest.get('model', '?')}` · "
        f"{manifest.get('isolation', '?')} isolation · "
        f"max {manifest.get('max_tries', '?')} tries · "
        f"{len(manifest.get('tasks') or [])} tasks · "
        f"phronix {manifest.get('phronix_version', '?')}",
        "",
    ]

    comparison = report.get("comparison") or {}
    verdict = comparison.get("verdict", "no_data")
    lines += [
        "## Verdict",
        "",
        f"**{verdict.replace('_', ' ')}** — {comparison.get('note', '')}",
        "",
    ]
    if "slope_delta" in comparison:
        lines += [
            f"- learning arm slope  `{comparison['resolve_slope_learning']:+.4f}` / task",
            f"- frozen control slope `{comparison['resolve_slope_control']:+.4f}` / task",
            f"- **delta** `{comparison['slope_delta']:+.4f}` "
            "(the part attributable to learning)",
            f"- reuse rate `{comparison['reuse_rate']:.2f}` "
            f"(cross-repo `{comparison.get('reuse_rate_cross_repo', 0):.2f}`)",
            "",
        ]

    lines += [
        "## Arms",
        "",
        "`Resolved@1` is first-attempt only, and it is the like-for-like number: "
        "retry budgets differ by arm on purpose, since a memoryless baseline "
        "retrying is resampling rather than a second, better-informed try.",
        "",
        "Tokens are split by activity. `solve` is the agent attempting the task, "
        "`research` is working out how it should be approached, `learn` is "
        "turning the result into stored knowledge. A phronix arm costing more in "
        "total is expected; whether the extra bought anything is a question about "
        "the `research` and `learn` columns specifically.",
        "",
        "| Arm | Resolved | Rate | Resolved@1 | Tries/task | Tokens | solve | research | learn | Tokens/resolved | Cost | Learned |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in ordered:
        s = summaries[arm]
        if not s.get("tasks"):
            continue
        learning = s["learning_rate"]
        # An arm that resolved nothing has no tokens-per-resolved; printing 0 or
        # infinity would both read as a measurement rather than as "undefined".
        per_resolved = (f"{s['tokens_per_resolved']:,}"
                        if s.get("tokens_per_resolved") else "—")
        lines.append(
            f"| `{arm}` | {s['resolved']}/{s['tasks']} | {s['resolve_rate']:.2f} "
            f"| {s.get('resolved_first_attempt', 0)}/{s['tasks']} "
            f"| {s['tries_mean']:.2f} | {s['tokens_total']:,} "
            f"| {s.get('tokens_solve', 0):,} | {s.get('tokens_research', 0):,} "
            f"| {s.get('tokens_learn', 0):,} | {per_resolved} "
            f"| ${s['cost_usd']:.2f} | {learning['skills_created']} |")

    lines += ["", "## Learning rate", "",
              "| Arm | Resolve slope (95% CI) | Significant | Reuse | Tries slope | Tokens slope |",
              "| --- | --- | :-: | ---: | ---: | ---: |"]
    for arm in ordered:
        s = summaries[arm]
        if not s.get("tasks"):
            continue
        learning = s["learning_rate"]
        lines.append(
            f"| `{arm}` | {_fmt_slope(learning['resolve_slope'], learning.get('resolve_slope_ci95'))} "
            f"| {'yes' if learning.get('resolve_slope_significant') else 'no'} "
            f"| {learning['reuse_rate']:.2f} "
            f"| {learning['tries_slope']:+.3f} | {learning['tokens_slope']:+,.0f} |")

    for arm in ordered:
        s = summaries[arm]
        if not s.get("curve"):
            continue
        lines += ["", f"### Curve — `{arm}` (rolling window)", "",
                  "| Tasks | Resolve | Tries | Tokens |", "| --- | ---: | ---: | ---: |"]
        for row in s["curve"]:
            lines.append(f"| {row['tasks']} | {row['resolve']:.2f} "
                         f"| {row['tries']:.2f} | {row['tokens']:,} |")

    lines += [
        "",
        "---",
        "",
        "Token counts for the `mini` and `opencode-bare` arms are scraped from agent "
        "output; the phronix arms are measured by the collector. Treat small token "
        "differences between those two groups as indicative, not exact.",
        "",
        "Slopes are fitted to a single fixed task order. A wide interval means the "
        "sample is too small to distinguish the effect from ordering noise — the "
        "answer is more tasks or more seeds, not a more confident reading of these.",
    ]
    return "\n".join(lines) + "\n"


def write(run_dir: Path, window: int = 10) -> Dict[str, Path]:
    report = build(run_dir, window=window)
    run_dir = Path(run_dir)
    markdown = run_dir / "report.md"
    payload = run_dir / "report.json"
    markdown.write_text(render(report))
    payload.write_text(json.dumps(report, indent=2) + "\n")
    return {"markdown": markdown, "json": payload}
