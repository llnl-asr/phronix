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

# Reserved status steps: good and critical.
OUTCOME = {"solved": "#0ca30c", "failed": "#d03b3b"}
# Bare is hatched throughout the paper as the arm whose retry budget is an
# assumption rather than a measurement.
ARM_HATCH = {"bare": "///", "phronix": ""}
SERIES = [
    ("bare", "solved", "Bare, solved"),
    ("bare", "failed", "Bare, failed"),
    ("phronix", "solved", "Phronix, solved"),
    ("phronix", "failed", "Phronix, failed"),
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
        for k in ("tasks", "attempts", "tokens_total"):
            r[k] = int(r[k])
        r["tokens_per_try"] = float(r["tokens_per_try"])
    return rows


def short(category: str) -> str:
    return category.split("/")[-1]


def build(rows: list[dict], size: tuple[float, float], out: Path, style: dict,
          top_n: int | None = 6) -> None:
    # Rank categories by how much work they represent, pooled over both modes,
    # so the two panels show the SAME categories in the same order.
    weight: dict[str, int] = {}
    for r in rows:
        weight[r["category"]] = weight.get(r["category"], 0) + r["attempts"]
    cats = sorted(weight, key=lambda c: -weight[c])
    if top_n:
        cats = cats[:top_n]
    n = len(cats)

    lookup = {(r["mode"], r["arm"], r["category"], r["outcome"]): r for r in rows}
    width = style["axes"]["bar_width"] / len(SERIES)
    modes = ["fresh", "reuse"]

    fig, axes = plt.subplots(1, len(modes), figsize=size, sharey=True,
                             squeeze=False)
    axes = axes[0]

    tallest = 0.0
    for ax, mode in zip(axes, modes):
        for si, (arm, outcome, _label) in enumerate(SERIES):
            vals = [lookup.get((mode, arm, c, outcome), {}).get("tokens_per_try", 0)
                    / SCALE for c in cats]
            tallest = max(tallest, max(vals, default=0))
            offs = [i - style["axes"]["bar_width"] / 2 + width * (si + 0.5)
                    for i in range(n)]
            hatch = ARM_HATCH[arm]
            ax.bar(offs, vals, width=width, color=OUTCOME[outcome], hatch=hatch,
                   edgecolor=style["text_secondary"] if hatch else style["surface"],
                   linewidth=1.0, zorder=3)

        ax.set_xticks(range(n))
        ax.set_xticklabels([short(c) for c in cats])
        ax.set_xlabel(f"Task category ({mode})")
        ax.set_xlim(-0.6, n - 0.4)
        ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
                zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in style["axes"]["spines"]:
            ax.spines[side].set_color(style["text_secondary"])

    axes[0].set_ylabel("Tokens per attempt (K)")
    # Headroom for the legend, which sits inside the first panel.
    figtools.set_ticks(axes[0], tallest * 1.35, TICK_INTERVALS)

    keys = [Patch(facecolor=OUTCOME[o], hatch=ARM_HATCH[a],
                  edgecolor=style["text_secondary"] if ARM_HATCH[a]
                  else style["surface"], label=lab)
            for a, o, lab in SERIES]
    axes[0].legend(handles=keys, frameon=False,
                   fontsize=plt.rcParams["legend.fontsize"], handlelength=1.6,
                   ncol=2, loc="upper left", bbox_to_anchor=(0.0, 1.0))

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}  ({size[0]}x{size[1]} in, {n} categories x {len(modes)} modes)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=HERE / "eval4_tokens.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--size", default="wide")
    ap.add_argument("--top-n", type=int, default=6)
    ap.add_argument("--out", type=Path, default=HERE / "eval4_tokens.pdf")
    args = ap.parse_args()

    style = load_style(args.style)
    build(read_rows(args.csv), tuple(style["dimensions"][args.size]),
          args.out, style, top_n=args.top_n)


if __name__ == "__main__":
    main()
