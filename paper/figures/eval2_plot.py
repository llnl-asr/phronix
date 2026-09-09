#!/usr/bin/env python3
"""Eval 2 -- what the system wrote down, and what it turned that into.

The stack is durable knowledge: skills and MCP tools the model produced. The
line is the raw tracking volume the stack was distilled from. Reading them
together is the point -- a model that tracks heavily but converts little is
doing bookkeeping, not learning.

Fresh and reuse runs are summed per model. Learning is almost entirely a fresh
run's doing (a reuse run finds the capability already written), while tracking
happens in both, so the pair is the model's whole story.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).parent

# Violet: a categorical slot neither stacked series uses, so the line never
# impersonates a bar.
TRACKING_COLOR = "#4a3aa7"

KINDS = [
    ("skills_learned", "Skills"),
    ("tools_learned", "MCP tools"),
]


def load_style(path: Path) -> dict:
    style = yaml.safe_load(path.read_text())
    font = style["font"]
    plt.rcParams.update({
        "font.size": font["size"],
        "font.family": font["family"],
        "font.sans-serif": font["sans_serif"],
        "axes.titlesize": font["size"],
        "axes.labelsize": font["size"],
        "xtick.labelsize": font["size"] - 4,
        "ytick.labelsize": font["size"] - 3,
        "legend.fontsize": font["size"] - 3,
        "figure.facecolor": style["surface"],
        "axes.facecolor": style["surface"],
        "savefig.facecolor": style["surface"],
        "text.color": style["text_primary"],
        "axes.labelcolor": style["text_primary"],
        "xtick.color": style["text_secondary"],
        "ytick.color": style["text_secondary"],
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    return style


def read_rows(path: Path) -> list[dict]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if k not in ("model", "mode", "run"):
                r[k] = int(v)
    return rows


def build(rows: list[dict], models: list[str], size: tuple[float, float],
          out: Path, style: dict) -> None:
    # Sum the run modes: one bar per model, not one per run.
    total: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["model"] in models:
            for field in ("skills_learned", "tools_learned", "entries_tracked",
                          "topics"):
                total[r["model"]][field] += r[field]

    colors = style["palette"]
    x = range(len(models))

    fig, ax = plt.subplots(figsize=size)

    bottom = [0.0] * len(models)
    for ki, (field, _label) in enumerate(KINDS):
        vals = [total[m][field] for m in models]
        ax.bar(x, vals, width=style["axes"]["bar_width"], bottom=bottom,
               color=colors[ki], edgecolor=style["surface"], linewidth=1.0,
               zorder=3)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xticks(list(x))
    ax.set_xticklabels(models)
    ax.set_xlabel("Model")
    ax.set_ylabel("# Learned")
    ax.set_xlim(-0.6, len(models) - 0.4)
    ax.set_ylim(0, max(bottom) * 1.12)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
            zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in style["axes"]["spines"]:
        ax.spines[side].set_color(style["text_secondary"])

    # Tracking volume on its own axis: it counts observation entries, not
    # capabilities, and runs an order of magnitude higher. The scales are not
    # comparable by height -- the line is read against the right-hand numbers.
    ax2 = ax.twinx()
    tracked = [total[m]["entries_tracked"] for m in models]
    ax2.plot(list(x), tracked, color=TRACKING_COLOR, marker="o", markersize=9,
             linewidth=2, markeredgecolor=style["surface"], markeredgewidth=1.5,
             zorder=5, clip_on=False)
    ax2.set_ylim(0, max(tracked) * 1.12)
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    ax2.set_ylabel("# Entries tracked", color=TRACKING_COLOR)
    ax2.tick_params(axis="y", colors=TRACKING_COLOR)
    for side in ("top", "left"):
        ax2.spines[side].set_visible(False)
    ax2.spines["right"].set_color(TRACKING_COLOR)

    # Below the axes, one row-major block, matching eval 1 so the two figures
    # read as one system.
    small = plt.rcParams["legend.fontsize"]
    kind_keys = [Patch(facecolor=colors[i], edgecolor=style["surface"], label=lab)
                 for i, (_, lab) in enumerate(KINDS)]
    line_key = [Line2D([0], [0], color=TRACKING_COLOR, marker="o", markersize=9,
                       linewidth=2, label="Entries tracked")]
    fig.legend(handles=kind_keys + line_key, frameon=False, fontsize=small,
               handlelength=1.6, ncol=3, loc="upper center",
               bbox_to_anchor=(0.5, 0.20))

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.34)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}  ({size[0]}x{size[1]} in, {len(models)} models)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=HERE / "eval2_tracking.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--models", nargs="*",
                    default=["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4"])
    ap.add_argument("--size", default="column",
                    help="named size from style.yaml")
    ap.add_argument("--out", type=Path, default=HERE / "eval2_tracking.pdf")
    args = ap.parse_args()

    style = load_style(args.style)
    rows = read_rows(args.csv)
    present = [m for m in args.models if any(r["model"] == m for r in rows)]
    missing = [m for m in args.models if m not in present]
    if missing:
        print(f"note: no rows for {', '.join(missing)} -- omitted")
    if not present:
        raise SystemExit("no requested model appears in the CSV")

    build(rows, present, tuple(style["dimensions"][args.size]), args.out, style)


if __name__ == "__main__":
    main()
