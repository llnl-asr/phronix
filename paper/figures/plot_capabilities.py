#!/usr/bin/env python3
"""Capabilities phronix built per task category, and how much they came back.

Three counts share one axis because they are the same unit -- capabilities --
so they can be compared by eye without the reader converting between scales.
Two of them are what a FRESH run wrote (it starts with an empty store, so
everything in it was built during the run); the third is what a REUSE run
loaded from what those fresh runs left behind. Splitting them by run mode is
what makes the third bar meaningful: a reuse run writes almost nothing
precisely because the capability it needed was already there.
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

HERE = Path(__file__).parent

# Fixed slot order: each series owns a colour by identity. Dropping a model
# from the figure must not repaint the series that remain.
SERIES = [
    ("skills_created", "fresh", "Skills created"),
    ("tools_created", "fresh", "MCP tools created"),
    ("skills_reused", "reuse", "Skills reused"),
    ("tools_reused", "reuse", "MCP tools reused"),
]


def load_style(path: Path) -> dict:
    style = yaml.safe_load(path.read_text())
    font = style["font"]
    plt.rcParams.update({
        "font.size": font["size"],
        "font.family": font["family"],
        "font.sans-serif": font["sans_serif"],
        # Everything derived from the base size, so raising it once raises
        # the whole figure coherently.
        "axes.titlesize": font["size"],
        "axes.labelsize": font["size"],
        "xtick.labelsize": font["size"] - 3,
        "ytick.labelsize": font["size"] - 3,
        "legend.fontsize": font["size"] - 3,
        "figure.facecolor": style["surface"],
        "axes.facecolor": style["surface"],
        "savefig.facecolor": style["surface"],
        "text.color": style["text_primary"],
        "axes.labelcolor": style["text_primary"],
        "xtick.color": style["text_secondary"],
        "ytick.color": style["text_secondary"],
        "pdf.fonttype": 42,   # embed as TrueType: selectable text in the PDF
        "ps.fonttype": 42,
    })
    return style


def read_rows(path: Path) -> list[dict]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if k not in ("model", "mode", "category"):
                r[k] = int(v)
    return rows


def short(category: str) -> str:
    """`scikit-learn/scikit-learn` -> `scikit-learn`; keep the axis readable."""
    return category.split("/")[-1]


# How much a canvas can hold before the columns stop being readable. The wide
# strip takes every category and one panel per model; the narrower sizes drop
# to the busiest categories, and the square is too small for per-model panels
# at all, so it pools the models into one.
FITS = {
    "wide":   {"top_n": None, "per_model": True},
    "column": {"top_n": 6, "per_model": False},
    "square": {"top_n": 4, "per_model": False},
}


def build(rows: list[dict], models: list[str], size: tuple[float, float],
          out: Path, style: dict, top_n: int | None = None,
          per_model: bool = True) -> None:
    # A category earns a column if any selected model touched it. Ordering by
    # total capability volume puts the busy categories first, so the eye reads
    # the distribution rather than the alphabet.
    volume: dict[str, int] = defaultdict(int)
    for r in rows:
        if r["model"] in models:
            volume[r["category"]] += sum(r[k] for k, _, _ in SERIES)
    cats = [c for c, v in sorted(volume.items(), key=lambda kv: -kv[1]) if v]
    if top_n:
        cats = cats[:top_n]

    lookup = {(r["model"], r["mode"], r["category"]): r for r in rows}
    colors = style["palette"]
    width = style["axes"]["bar_width"] / len(SERIES)

    panels = [(m, [m]) for m in models] if per_model else [
        (" + ".join(models), models)]

    fig, axes = plt.subplots(1, len(panels), figsize=size, sharey=True,
                             squeeze=False)
    axes = axes[0]

    for ax, (_label, group) in zip(axes, panels):
        for si, (field, mode, label) in enumerate(SERIES):
            vals = [sum(lookup.get((m, mode, c), {}).get(field, 0) for m in group)
                    for c in cats]
            offs = [i - style["axes"]["bar_width"] / 2 + width * (si + 0.5)
                    for i in range(len(cats))]
            ax.bar(offs, vals, width=width, label=label, color=colors[si],
                   # A 2px surface gap between adjacent fills keeps the group
                   # legible where two bars are near-equal.
                   edgecolor=style["surface"], linewidth=1.0, zorder=3)

        ax.set_xticks(range(len(cats)))
        ax.set_xticklabels([short(c) for c in cats], rotation=45,
                           ha="right", rotation_mode="anchor")
        ax.set_xlim(-0.6, len(cats) - 0.4)
        ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
                zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in style["axes"]["spines"]:
            ax.spines[side].set_color(style["text_secondary"])

    # Upright and broken over two lines: a rotated label costs the reader a
    # head-tilt, and at 18pt "# Capabilities" on one line pushes the plot area
    # off the left of a single-column canvas.
    axes[0].set_ylabel("#\nCapabilities", rotation=0, ha="center",
                       va="center", labelpad=38)
    # Headroom for the legend, so it sits in empty space instead of on top of
    # the tallest bars -- which is what it does on the small canvases, where
    # there is no slack anywhere inside the plot area.
    top = max((b.get_height() for ax in axes for b in ax.patches), default=1)
    axes[0].set_ylim(0, top * 1.32)
    # One legend for the figure: the series mean the same thing in every panel,
    # and three copies of it would cost space the categories need.
    axes[0].legend(frameon=False, loc="upper right",
                   fontsize=plt.rcParams["legend.fontsize"] - (3 if size[0] < 6 else 0))

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}  ({size[0]}x{size[1]} in, {len(cats)} categories)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=HERE / "capabilities_by_category.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--models", nargs="*",
                    default=["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4"])
    ap.add_argument("--sizes", nargs="*", default=["column"],
                    help="named sizes from style.yaml (wide, column, square)")
    ap.add_argument("--top-n", type=int, default=None,
                    help="keep only the N busiest categories (default: per size)")
    ap.add_argument("--out", type=Path, default=HERE / "capabilities_by_category")
    args = ap.parse_args()

    style = load_style(args.style)
    rows = read_rows(args.csv)
    present = [m for m in args.models if any(r["model"] == m for r in rows)]
    missing = [m for m in args.models if m not in present]
    if missing:
        print(f"note: no rows for {', '.join(missing)} -- omitted")
    if not present:
        raise SystemExit("no requested model appears in the CSV")

    for name in args.sizes:
        size = tuple(style["dimensions"][name])
        suffix = "" if name == "column" else f"-{name}"
        fit = FITS.get(name, {"top_n": None, "per_model": True})
        build(rows, present, size,
              args.out.with_name(args.out.name + suffix + ".pdf"), style,
              top_n=args.top_n if args.top_n is not None else fit["top_n"],
              per_model=fit["per_model"])


if __name__ == "__main__":
    main()
