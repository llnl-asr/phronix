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
from matplotlib.patches import Patch

import figtools

HERE = Path(__file__).parent
# Whole attempts on the left axis -- an axis of attempts should not offer to
# read 4.5 of them -- with enough intervals that the bars clear the top third,
# which is where the legend sits.
TICK_INTERVALS = 8

# Attempt series (left axis). Colours are slots the research stack does not
# use, so a cost bar can never be mistaken for a knowledge bar.
ATTEMPTS = [
    ("bare_attempts_est", "#eda100", "///", "Bare (est.)"),
    ("solved_attempts_mean", "#1baf7a", "", "Phronix, solved"),
    ("failed_attempts_mean", "#4a3aa7", "", "Phronix, failed"),
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
            if k != "category":
                r[k] = float(v) if "." in v else int(v)
    return rows


def short(category: str) -> str:
    return category.split("/")[-1]


def build(rows: list[dict], size: tuple[float, float], out: Path, style: dict,
          top_n: int | None = 6) -> None:
    # Busiest categories first: the eye should read the distribution, not the
    # alphabet.
    rows = sorted(rows, key=lambda r: -(r["solved_tasks"] + r["failed_tasks"]))
    if top_n:
        rows = rows[:top_n]
    cats = [r["category"] for r in rows]
    n = len(cats)

    # Four bars per category: three attempt bars then the research stack, with
    # the stack set slightly apart so it reads as a different quantity.
    slots = len(ATTEMPTS) + 1
    width = style["axes"]["bar_width"] / slots
    fig, ax = plt.subplots(figsize=size)
    ax2 = ax.twinx()

    def offset(slot: int) -> list[float]:
        return [i - style["axes"]["bar_width"] / 2 + width * (slot + 0.5)
                for i in range(n)]

    for si, (field, color, hatch, _label) in enumerate(ATTEMPTS):
        ax.bar(offset(si), [r[field] for r in rows], width=width, color=color,
               hatch=hatch,
               edgecolor=style["text_secondary"] if hatch else style["surface"],
               linewidth=1.0, zorder=3)

    bottom = [0.0] * n
    for field, color, _label in RESEARCH:
        vals = [r[field] for r in rows]
        ax2.bar(offset(slots - 1), vals, width=width, bottom=bottom, color=color,
                edgecolor=style["surface"], linewidth=1.0, zorder=3)
        bottom = [b + v for b, v in zip(bottom, vals)]

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

    keys = [Patch(facecolor=c, hatch=h,
                  edgecolor=style["text_secondary"] if h else style["surface"],
                  label=lab) for _, c, h, lab in ATTEMPTS]
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
    ap.add_argument("--out", type=Path, default=HERE / "eval3_retries.pdf")
    args = ap.parse_args()

    style = load_style(args.style)
    build(read_rows(args.csv), tuple(style["dimensions"][args.size]),
          args.out, style, top_n=args.top_n)


if __name__ == "__main__":
    main()
