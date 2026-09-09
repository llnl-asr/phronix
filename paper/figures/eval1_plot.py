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
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, PercentFormatter
from matplotlib.patches import Patch

HERE = Path(__file__).parent

# Violet: a categorical slot none of the stacked series uses, so the line
# never impersonates a bar.
DETERMINISM_COLOR = "#4a3aa7"

# Fixed slot order: each series owns a colour by identity. Dropping a model
# from the figure must not repaint the series that remain.
# Two encodings, each carrying one variable, so neither is read off colour
# alone: COLOUR says what kind of capability it is, HATCH says which run mode
# produced the number. A stack is therefore total capabilities, and the pair
# of stacks in a category compares building against reusing.
KINDS = [
    ("skills", "Skills"),
    ("tools", "MCP tools"),
]
MODES = [
    ("fresh", "", "Fresh (created)"),
    ("reuse", "//", "Reuse (reused)"),
]
# Which CSV column holds each (kind, mode) cell. A fresh run's number is what
# it built; a reuse run's is what it loaded. Different questions, same unit.
FIELD = {
    ("skills", "fresh"): "skills_created",
    ("tools", "fresh"): "tools_created",
    ("skills", "reuse"): "skills_reused",
    ("tools", "reuse"): "tools_reused",
}


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
            volume[r["category"]] += sum(r[f] for f in FIELD.values())
    cats = [c for c, v in sorted(volume.items(), key=lambda kv: -kv[1]) if v]
    if top_n:
        cats = cats[:top_n]

    lookup = {(r["model"], r["mode"], r["category"]): r for r in rows}
    colors = style["palette"]
    # Two bars per category, so each gets half the group's width.
    width = style["axes"]["bar_width"] / len(MODES)

    panels = [(m, [m]) for m in models] if per_model else [
        (" + ".join(models), models)]

    fig, axes = plt.subplots(1, len(panels), figsize=size, sharey=True,
                             squeeze=False)
    axes = axes[0]

    for ax, (_label, group) in zip(axes, panels):
        for mi, (mode, hatch, _) in enumerate(MODES):
            offs = [i - style["axes"]["bar_width"] / 2 + width * (mi + 0.5)
                    for i in range(len(cats))]
            bottom = [0.0] * len(cats)
            for ki, (kind, _) in enumerate(KINDS):
                field = FIELD[(kind, mode)]
                vals = [sum(lookup.get((m, mode, c), {}).get(field, 0)
                            for m in group) for c in cats]
                ax.bar(offs, vals, width=width, bottom=bottom,
                       color=colors[ki], hatch=hatch,
                       # A hatched bar needs a visible edge to draw the hatch
                       # in; an unhatched one uses the surface colour so the
                       # stacked segments read as separated rather than fused.
                       edgecolor=style["text_secondary"] if hatch
                       else style["surface"],
                       linewidth=1.0, zorder=3)
                bottom = [b + v for b, v in zip(bottom, vals)]

        # The determinism claim, conditioned on there being something to be
        # deterministic ABOUT: of the tasks a fresh run solved -- and so left a
        # working skill for -- how many did the reuse run then get right on
        # the first attempt? Scoring against all tasks instead would fold in
        # every task no run ever solved, where a first-try miss says nothing
        # about reuse. A rate, not a count, because categories hold different
        # numbers of tasks.
        ax2 = ax.twinx()
        firsts = []
        for c in cats:
            hit = sum(lookup.get((m, "reuse", c), {}).get("first_try_eligible", 0)
                      for m in group)
            n = sum(lookup.get((m, "reuse", c), {}).get("eligible", 0)
                    for m in group)
            # A category no run ever solved has an empty denominator: there is
            # no rate to draw, and drawing 0% would assert a failure that was
            # never measured.
            firsts.append(100.0 * hit / n if n else float("nan"))
        ax2.plot(range(len(cats)), firsts, color=DETERMINISM_COLOR,
                 marker="o", markersize=9, linewidth=2,
                 markeredgecolor=style["surface"], markeredgewidth=1.5,
                 zorder=5, clip_on=False)
        # Fixed full-range scale: a rate auto-scaled to its own maximum makes
        # a weak result look like a strong one.
        ax2.set_ylim(0, 100)
        ax2.yaxis.set_major_formatter(PercentFormatter())
        ax2.set_ylabel("First-try solve",
                       color=DETERMINISM_COLOR)
        ax2.tick_params(axis="y", colors=DETERMINISM_COLOR)
        for side in ("top", "left"):
            ax2.spines[side].set_visible(False)
        ax2.spines["right"].set_color(DETERMINISM_COLOR)

        ax.set_xticks(range(len(cats)))
        ax.set_xticklabels([short(c) for c in cats])
        ax.set_xlabel("Task category")
        ax.set_xlim(-0.6, len(cats) - 0.4)
        ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
                zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in style["axes"]["spines"]:
            ax.spines[side].set_color(style["text_secondary"])

    axes[0].set_ylabel("# Capabilities")
    # Headroom for the legends, so they sit in empty space rather than on top
    # of the tallest stack.
    # A fixed scale with round ticks, so the reader counts in 40s and two
    # printings of this figure are comparable even if the data moves.
    axes[0].set_ylim(0, 200)
    axes[0].yaxis.set_major_locator(MultipleLocator(40))
    tallest = max((b.get_y() + b.get_height() for ax in axes
                   for b in ax.patches), default=0)
    if tallest > 200:
        print(f"warning: tallest stack is {tallest:.0f}, clipped by the 0-200 axis")

    # One legend per encoding. Collapsing them into four combined entries
    # would imply four independent series and hide that colour and hatch are
    # answering two different questions.
    kind_keys = [Patch(facecolor=style["palette"][i], edgecolor=style["surface"],
                       label=label) for i, (_, label) in enumerate(KINDS)]
    line_key = [Line2D([0], [0], color=DETERMINISM_COLOR, marker="o",
                       markersize=9, linewidth=2,
                       label="% solved first try")]
    mode_keys = [Patch(facecolor=style["surface"], hatch=hatch,
                       edgecolor=style["text_secondary"], label=label)
                 for _, hatch, label in MODES]
    # Inside, low and to the right: the rate line runs high once it is
    # conditioned on tasks that had a skill, so the free band is underneath it
    # rather than above the bars. Headroom on the left axis (below) shortens
    # the stacks until that band is genuinely clear.
    # Top-aligned inside the plot. The rate line is drawn on the twin axes,
    # which render after this one, so the line passes OVER the legend instead
    # of the legend having to dodge it -- which is what forced the type down
    # a size and the bars into a third of the canvas.
    small = plt.rcParams["legend.fontsize"]
    axes[0].legend(handles=kind_keys + mode_keys + line_key, frameon=False,
                   fontsize=small, handlelength=1.6, ncol=2,
                   loc="upper left", bbox_to_anchor=(0.22, 1.0))

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}  ({size[0]}x{size[1]} in, {len(cats)} categories)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=HERE / "eval1_capabilities.csv")
    ap.add_argument("--style", type=Path, default=HERE / "style.yaml")
    ap.add_argument("--models", nargs="*",
                    default=["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4"])
    ap.add_argument("--sizes", nargs="*", default=["column"],
                    help="named sizes from style.yaml (wide, column, square)")
    ap.add_argument("--top-n", type=int, default=None,
                    help="keep only the N busiest categories (default: per size)")
    ap.add_argument("--out", type=Path, default=HERE / "eval1_capabilities")
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
