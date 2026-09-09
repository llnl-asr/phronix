#!/usr/bin/env python3
"""Eval 4 -- token cost of one attempt, fresh beside reuse.

Colour carries the outcome and hatch carries the arm, so neither is read off
colour alone. Green and red here are the reserved status steps rather than
categorical slots, because success and failure ARE a status -- and they always
appear with a written label, never colour alone.

Per attempt, not per task: phronix retries and bare does not, so a per-task
total would compare a budget against a single shot.
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
TICK_INTERVALS = 5
SCALE = 1_000  # plot thousands of tokens; raw counts need six digits per tick

# Reserved status steps: good and critical. Success and failure are a status,
# not two categories, and they always carry a written label.
OUTCOME = [
    ("solved_per_try", "#0ca30c", "Solved"),
    ("failed_per_try", "#d03b3b", "Failed"),
]
# Three arms, told apart by texture so the two status colours keep their one
# job. Phronix-fresh is the plain one; the other two are marked.
GROUPS = [
    ("bare", "///", "Bare"),
    ("phronix-fresh", "", "Phronix, fresh"),
    ("phronix-reuse", "\\\\", "Phronix, reuse"),
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
        for k in ("tasks", "attempts", "tokens_total", "solved_tasks",
                  "failed_tasks"):
            r[k] = int(r[k])
        for k in ("tokens_per_try", "solved_per_try", "failed_per_try"):
            r[k] = float(r[k])
    return rows


def short(category: str) -> str:
    return category.split("/")[-1]


def build(rows: list[dict], size: tuple[float, float], out: Path, style: dict,
          top_n: int | None = 6) -> None:
    # Rank categories by pooled attempt count, so the busiest work leads.
    weight: dict[str, int] = {}
    for r in rows:
        weight[r["category"]] = weight.get(r["category"], 0) + r["attempts"]
    cats = sorted(weight, key=lambda c: -weight[c])
    if top_n:
        cats = cats[:top_n]
    n = len(cats)

    lookup = {(r["group"], r["category"]): r for r in rows}
    width = style["axes"]["bar_width"] / len(GROUPS)

    fig, ax = plt.subplots(figsize=size)

    tallest = 0.0
    for gi, (group, hatch, _label) in enumerate(GROUPS):
        offs = [i - style["axes"]["bar_width"] / 2 + width * (gi + 0.5)
                for i in range(n)]
        bottom = [0.0] * n
        for field, color, _lab in OUTCOME:
            vals = [lookup.get((group, c), {}).get(field, 0.0) / SCALE
                    for c in cats]
            ax.bar(offs, vals, width=width, bottom=bottom, color=color,
                   hatch=hatch,
                   edgecolor=style["text_secondary"] if hatch else style["surface"],
                   linewidth=1.0, zorder=3)
            bottom = [b + v for b, v in zip(bottom, vals)]
        tallest = max(tallest, max(bottom, default=0.0))

    ax.set_xticks(range(n))
    ax.set_xticklabels([short(c) for c in cats])
    ax.set_xlabel("Task category")
    ax.set_ylabel("Tokens per attempt (K)")
    ax.set_xlim(-0.6, n - 0.4)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
            zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in style["axes"]["spines"]:
        ax.spines[side].set_color(style["text_secondary"])
    # Headroom for the legend, which sits inside.
    figtools.set_ticks(ax, tallest * 1.42, TICK_INTERVALS)

    # Two keys, one per encoding: colour says outcome, texture says arm.
    # Six combined entries would imply six independent series.
    keys = [Patch(facecolor=c, edgecolor=style["surface"], label=lab)
            for _, c, lab in OUTCOME]
    keys += [Patch(facecolor=style["surface"], hatch=h,
                   edgecolor=style["text_secondary"], label=lab)
             for _, h, lab in GROUPS]
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
    ap.add_argument("--csv", type=Path, default=HERE / "eval4_tokens.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--size", default="column")
    ap.add_argument("--top-n", type=int, default=6)
    ap.add_argument("--out", type=Path, default=HERE / "eval4_tokens.pdf")
    args = ap.parse_args()

    style = load_style(args.style)
    build(read_rows(args.csv), tuple(style["dimensions"][args.size]),
          args.out, style, top_n=args.top_n)


if __name__ == "__main__":
    main()
