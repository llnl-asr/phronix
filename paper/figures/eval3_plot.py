#!/usr/bin/env python3
"""Eval 3 -- what a task costs in attempts, against what research it produced.

Left axis, three bars: the attempt budget a bare agent would need (an
estimate -- hatched, because bare has no retry loop and was only ever run
once), and phronix's measured attempts split by outcome. Splitting matters:
a solved task's count is what the research saved, a failed one's is the
budget cap being spent.

Right axis, one stacked bar: what the research left behind, topics
investigated and MCP tools built.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import figtools

HERE = Path(__file__).parent
# Whole attempts on the left axis -- an axis of attempts should not offer to
# read 4.5 of them -- with enough intervals that the bars clear the top third,
# which is where the legend sits.
TICK_INTERVALS = 8

# Attempt series (left axis), drawn as LINES. Cost and knowledge are
# different kinds of quantity, and as four bars in a row they read as one
# series of four; as lines over bars the distinction is structural rather
# than something the reader has to hold in their head from the legend.
# Bare is dashed because its value is assumed, not measured.
ATTEMPTS = [
    ("bare_attempts_est", "#eda100", "--", "Base (est.)", "count_bare"),
    ("solved_attempts_mean", "#1baf7a", "-", "Phronix, solved", "solved_tasks"),
    ("failed_attempts_mean", "#4a3aa7", "-", "Phronix, failed", "failed_tasks"),
]
# Research stack (right axis), in the same colours these two things wear in
# every other figure in the paper.
RESEARCH = [
    ("research_topics", "#2a78d6", "Research topics"),
    ("research_tools", "#eb6834", "MCP tools"),
]


def load_style(path: Path) -> dict:
    style = yaml.safe_load(path.read_text())
    font = style["font"]
    plt.rcParams.update({
        "font.size": font["size"], "font.family": font["family"],
        "font.sans-serif": font["sans_serif"],
        "axes.titlesize": font["size"], "axes.labelsize": font["size"],
        "xtick.labelsize": font["size"] - 4, "ytick.labelsize": font["size"] - 3,
        "legend.fontsize": font["size"] - 3,
        "figure.facecolor": style["surface"], "axes.facecolor": style["surface"],
        "savefig.facecolor": style["surface"], "text.color": style["text_primary"],
        "axes.labelcolor": style["text_primary"],
        "xtick.color": style["text_secondary"], "ytick.color": style["text_secondary"],
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    return style


def read_rows(path: Path) -> list[dict]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if k not in ("category", "model", "mode", "run"):
                r[k] = float(v) if "." in v else int(v)
    return rows


def short(category: str) -> str:
    """The axis label for a category — see figtools.short_name."""
    return figtools.short_name(category)


ALL_FIELDS = [f for f, *_ in ATTEMPTS] + [f for f, *_ in RESEARCH] + [
    "solved_tasks", "failed_tasks", "bare_tasks"]


#: Fields that ADD when the two run modes are pooled, rather than averaging.
SUMMED = {"research_topics", "research_tools", "solved_tasks", "failed_tasks",
          "bare_tasks"}


def collapse(rows: list[dict]) -> list[dict]:
    """One row per category: every field a (mean, sd, n) across REPEATS.

    Repeats are grouped WITHIN a run mode before the modes are pooled, and
    that ordering is the whole point. A model contributes a fresh run and a
    reuse run; treating those two as two repeats of one condition reports the
    fresh-versus-reuse difference as run-to-run noise, which is the largest
    signal in the sweep laid out as though it were error. Grouped by mode
    first, the spread is between repeats of the SAME condition, which is what
    an error bar is supposed to mean.

    Modes are then pooled as the figure has always pooled them: counts add,
    per-task means combine weighted by the tasks behind them, and the two
    modes' spreads add in quadrature.
    """
    out: dict[str, dict] = {}
    for cat in {r["category"] for r in rows}:
        mine = [r for r in rows if r["category"] == cat]
        modes = sorted({r["mode"] for r in mine})
        cell = {"category": cat}
        for field in ALL_FIELDS:
            per_mode = []
            for mode in modes:
                got = figtools.agg([r for r in mine if r["mode"] == mode],
                                   lambda _r: "all", field)
                if "all" in got:
                    per_mode.append(got["all"])
            if not per_mode:
                cell[field] = (0.0, None, 0)
                continue
            runs = max(v[2] for v in per_mode)
            sd = ([v[1] for v in per_mode] if any(v[1] for v in per_mode)
                  else None)
            quad = (sum((x or 0) ** 2 for x in sd) ** 0.5) if sd else None
            if field in SUMMED:
                cell[field] = (sum(v[0] for v in per_mode), quad, runs)
            else:
                # A mean per task: weight each mode by how many tasks stand
                # behind it, or a mode with one task would count as much as
                # one with twenty.
                weight_field = ("solved_tasks" if "solved" in field
                                else "failed_tasks" if "failed" in field
                                else None)
                if weight_field is None:
                    cell[field] = (sum(v[0] for v in per_mode) / len(per_mode),
                                   quad, runs)
                    continue
                num = den = 0.0
                for mode, v in zip(modes, per_mode):
                    w = figtools.agg([r for r in mine if r["mode"] == mode],
                                     lambda _r: "all", weight_field)
                    w = w.get("all", (0.0, None, 0))[0]
                    num += v[0] * w
                    den += w
                cell[field] = (num / den if den else 0.0, quad, runs)
        out[cat] = cell
    return list(out.values())


def build(rows: list[dict], size: tuple[float, float], out: Path, style: dict,
          top_n: int | None = 6) -> None:
    rows = collapse(rows)
    # Busiest categories first: the eye should read the distribution, not the
    # alphabet.
    # Canonical order, shared with every other figure (figtools).
    ranked = [r["category"] for r in
              sorted(rows, key=lambda r: -(r["solved_tasks"][0] + r["failed_tasks"][0]))]
    keep = figtools.top_categories(ranked, top_n)
    order = {c: i for i, c in enumerate(keep)}
    rows = sorted((r for r in rows if r["category"] in order),
                  key=lambda r: order[r["category"]])
    cats = [r["category"] for r in rows]
    n = len(cats)
    spread_note: list = []

    # Four bars per category: three attempt bars then the research stack, with
    # the stack set slightly apart so it reads as a different quantity.
    fig, ax = plt.subplots(figsize=size)
    ax2 = ax.twinx()

    # The research stack is the only bar now, so it takes the whole slot.
    bottom = [0.0] * n
    for field, color, _label in RESEARCH:
        vals = [r[field][0] for r in rows]
        ax2.bar(range(n), vals, width=style["axes"]["bar_width"] * 0.6,
                bottom=bottom, color=color, edgecolor=style["surface"],
                linewidth=1.0, zorder=2)
        bottom = [b + v for b, v in zip(bottom, vals)]
    # On the stack total, for the same reason as eval 1: the segments are
    # parts of one measured height, and one interval per segment cannot be
    # added up by eye.
    stack_sd = []
    for r in rows:
        sds = [r[f][1] for f, *_ in RESEARCH]
        ns = max(r[f][2] for f, *_ in RESEARCH)
        # Summed in quadrature: the two segments are counted separately per
        # run, so the height's variance is their variances added.
        tot = (sum(sd ** 2 for sd in sds if sd) ** 0.5) if any(sds) else None
        stack_sd.append((sum(r[f][0] for f, *_ in RESEARCH), tot, ns))
    # Means only on this figure.
    #
    # Four series share these axes -- three attempt lines and a two-part stack
    # -- and whiskers on all of them produced more interval than data: the
    # verticals collided with the markers and with each other, and the reader
    # could not tell which bar an arm belonged to. The spread is still in the
    # CSV for anyone who wants it; the figure shows the average.
    spread_note.extend(stack_sd)

    for field, color, dash, _label, count in ATTEMPTS:
        # A category with no task of that outcome has no mean to plot --
        # astropy solved nothing, and a zero there would claim it solved
        # something in zero attempts.
        # A category with no task of that outcome plots ZERO, not a gap.
        #
        # The gap was deliberate once -- it said "never measured" rather than
        # "measured as none" -- but it reads as a broken line and leaves the
        # eye to guess whether the series stops or dips. Zero is the honest
        # reading here: the category HAS tasks, and none of them ended that
        # way, which is a measurement rather than an absence.
        vals = [r[field][0] if (count == "count_bare" or r[count][0]) else 0.0
                for r in rows]
        ax.plot(range(n), vals, color=color, linestyle=dash, marker="o",
                markersize=9, linewidth=2, markeredgecolor=style["surface"],
                markeredgewidth=1.5, zorder=5, clip_on=False)
        spread_note.extend(r[field] for r in rows)

    # Twin axes draw in creation order, so the bars would cover the lines.
    # Lift the line axes above and let the bars show through it.
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.set_xticks(range(n))
    ax.set_xticklabels([short(c) for c in cats])
    ax.set_xlabel("Task category")
    ax.set_ylabel("# Attempts")
    ax.set_xlim(-0.6, n - 0.4)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
            zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in style["axes"]["spines"]:
        ax.spines[side].set_color(style["text_secondary"])

    ax2.set_ylabel("# Research output", color=RESEARCH[0][1])
    ax2.tick_params(axis="y", colors=RESEARCH[0][1])
    for side in ("top", "left"):
        ax2.spines[side].set_visible(False)
    ax2.spines["right"].set_color(RESEARCH[0][1])

    # Both axes get the same number of majors, so one set of horizontal rules
    # serves both scales.
    figtools.pair_axes(ax, ax2, 0, max(bottom) * 1.5,
                       intervals=TICK_INTERVALS, left_step=1)

    keys = [Line2D([0], [0], color=c, linestyle=d, marker="o", markersize=9,
                   linewidth=2, label=lab) for _, c, d, lab, _ in ATTEMPTS]
    keys += [Patch(facecolor=c, edgecolor=style["surface"], label=lab)
             for _, c, lab in RESEARCH]
    # Inside, across the top: the headroom above keeps every bar clear of it.
    ax.legend(handles=keys, frameon=False,
              fontsize=plt.rcParams["legend.fontsize"], handlelength=1.6,
              ncol=3, loc="upper left", bbox_to_anchor=(0.0, 1.0),
              columnspacing=1.4)


    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}  ({size[0]}x{size[1]} in, {n} categories)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=HERE / "eval3_retries.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--size", default="column")
    ap.add_argument("--top-n", type=int, default=6)
    ap.add_argument("--models", nargs="*", default=figtools.MODELS,
                    help="one FIGURE per model, lettered a, b, c")
    ap.add_argument("--out", type=Path, default=HERE / "eval3_retries")
    args = ap.parse_args()

    style = load_style(args.style)
    rows = read_rows(args.csv)
    present = [m for m in args.models if any(r["model"] == m for r in rows)]
    missing = [m for m in args.models if m not in present]
    if missing:
        print(f"note: no rows for {', '.join(missing)} -- omitted")
    if not present:
        raise SystemExit("no requested model appears in the CSV")

    for i, model in enumerate(present):
        build([r for r in rows if r["model"] == model],
              tuple(style["dimensions"][args.size]),
              figtools.panel_out(args.out, i), style, top_n=args.top_n)


if __name__ == "__main__":
    main()
