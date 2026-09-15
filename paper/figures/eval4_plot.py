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
SCALE = 1_000_000  # millions: "1.6" where "1600" was, which is where the
                   # horizontal room for three label rows comes from

# Reserved status steps: good and critical. Success and failure are a status,
# not two categories, and they always carry a written label.
OUTCOME = [
    ("solved_per_task", "#0ca30c", "Solved"),
    ("failed_per_task", "#d03b3b", "Failed"),
]
# Three arms, told apart by texture so the two status colours keep their one
# job. Phronix-fresh is the plain one; the other two are marked.
#: (key, arm, mode) — the arm and mode become the two label rows under the
#: axis, so the bars need no texture to tell them apart. Hatching was carrying
#: that job and cost the figure a whole legend block to explain; a bar sitting
#: under `phronix / reused` says the same thing without a key.
GROUPS = [
    ("bare", "base", "f"),
    ("phronix-fresh", "phronix", "f"),
    ("phronix-reuse", "phronix", "r"),
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
        for k in ("tokens_per_task", "solved_per_task", "failed_per_task"):
            r[k] = float(r[k])
    return rows


def short(category: str) -> str:
    """The axis label for a category — see figtools.short_name."""
    return figtools.short_name(category)


def build(rows: list[dict], size: tuple[float, float], out: Path, style: dict,
          top_n: int | None = 6) -> None:
    # Rank categories by pooled attempt count, so the busiest work leads.
    # Rank by the work the FRESH arms did: the reuse group is a filtered
    # subset by design, so letting it vote would rank categories by how much
    # reuse succeeded rather than by how much work they represent.
    weight: dict[str, int] = {}
    for r in rows:
        if r["group"] != "phronix-reuse":
            weight[r["category"]] = weight.get(r["category"], 0) + r["attempts"]
    # Canonical order, shared with every other figure (figtools).
    ranked = sorted(weight, key=lambda c: -weight[c])
    cats = figtools.top_categories(ranked, top_n)
    n = len(cats)

    # Mean over REPEATS. `group` already separates the three arms, so runs
    # sharing a group really are repeats of one condition -- unlike eval 3,
    # where fresh and reuse had to be split apart first.
    #
    # This replaced `{(group, category): row}`, which kept whichever row came
    # last and would have silently plotted one repeat out of five.
    def cellsof(group: str, cat: str) -> list[dict]:
        return [r for r in rows if r["group"] == group and r["category"] == cat]

    def mean_of(group: str, cat: str, field: str) -> float:
        got = cellsof(group, cat)
        return sum(r[field] for r in got) / len(got) if got else 0.0

    def segment_spread(group: str, cat: str, field: str) -> tuple:
        """(mean, sd, n) of ONE segment of a column, across runs.

        Per segment rather than per column. A single interval on the stack
        total says how far the whole bar moves but not which half moved, and
        it lands on the boundary between two colours where it reads as
        belonging to neither.
        """
        per_run = [r[field] / SCALE for r in cellsof(group, cat)]
        got = figtools.agg([{"v": v} for v in per_run], lambda _r: "all", "v")
        return got.get("all", (0.0, None, 0))


    def darker(hex_colour: str, factor: float = 0.62) -> tuple:
        """The same hue, dark enough to read against its own bar."""
        from matplotlib.colors import to_rgb

        return tuple(c * factor for c in to_rgb(hex_colour))

    # Wider than the shared bar_width: three bars per category need the room,
    # and closing the gap between categories is what lets `base` and
    # `phronix` sit side by side on the same row without touching.
    group_width = 0.94
    width = group_width / len(GROUPS)

    fig, ax = plt.subplots(figsize=size)
    spread_note: list = []

    tallest = 0.0
    for gi, (group, _arm, _mode) in enumerate(GROUPS):
        offs = [i - group_width / 2 + width * (gi + 0.5) for i in range(n)]
        bottom = [0.0] * n
        # Each segment's interval is drawn where that segment ENDS, and the
        # two are nudged apart so they never sit on top of each other or on
        # the boundary between the colours.
        lanes = [-0.22, 0.22]
        for si, (field, color, _lab) in enumerate(OUTCOME):
            vals = [mean_of(group, c, field) / SCALE for c in cats]
            ax.bar(offs, vals, width=width, bottom=bottom, color=color,
                   edgecolor=style["surface"], linewidth=1.0, zorder=3)
            bottom = [b + v for b, v in zip(bottom, vals)]

            spreads = [segment_spread(group, c, field) for c in cats]
            yerr = figtools.errorbars_at(bottom, spreads)
            if yerr:
                lane = [o + width * lanes[si] for o in offs]
                ax.errorbar(lane, bottom, yerr=yerr, fmt="none",
                            ecolor=darker(color), elinewidth=1.6,
                            capsize=3, capthick=1.6, zorder=6)
                tallest = max(tallest,
                              max((b + e for b, e in zip(bottom, yerr[1])),
                                  default=0.0))
            spread_note.extend(spreads)
        tallest = max(tallest, max(bottom, default=0.0))

    # Three rows under the axis: mode, then arm, then category.
    #
    # The mode row sits on every bar, the arm row spans the bars it owns (one
    # for base, two for phronix) and the category row spans the group. Written
    # as text in blended coordinates rather than as ticks, because matplotlib
    # gives one tick label per position and this needs three at different
    # depths.
    from matplotlib.transforms import blended_transform_factory

    tx = blended_transform_factory(ax.transData, ax.transAxes)
    # Small enough that `base` and `phronix` clear each other: they sit
    # 1.5 bar-widths apart, about 39pt at column size, and the pair needs
    # roughly half their combined width between centres.
    small = plt.rcParams["legend.fontsize"] - 5
    half = group_width / 2
    for i in range(n):
        centres = [i - half + width * (gi + 0.5) for gi in range(len(GROUPS))]
        # Rotated, because three modes have to sit under three bars inside one
        # category's width -- about 0.4in at column size, where `reused` set
        # horizontally is wider than the bar it labels and runs into its
        # neighbours. Upright it costs no horizontal room at all.
        # Base carries no mode, so it is named in the top row and the second
        # row holds only `phronix`, spanning its two bars. Writing `base` in
        # the second row as well put it a third of a bar-width from `phronix`
        # and the two ran together.
        # Single letters, so the row needs no rotation: `f` and `r` sit
        # upright under their bars and the legend says what they stand for.
        for (_key, _arm, mode), cx in zip(GROUPS, centres):
            ax.text(cx, -0.03, mode, transform=tx, ha="center", va="top",
                    fontsize=small, color=style["text_secondary"])
        # Both arms on one row, so `base` reads as phronix's peer rather than
        # as one of its modes.
        ax.text(centres[0], -0.12, "base", transform=tx, ha="center", va="top",
                fontsize=small, color=style["text_primary"])
        ax.text((centres[1] + centres[2]) / 2, -0.12, "phronix", transform=tx,
                ha="center", va="top", fontsize=small,
                color=style["text_primary"])
        ax.text(i, -0.22, short(cats[i]), transform=tx, ha="center", va="top",
                fontsize=plt.rcParams["xtick.labelsize"],
                color=style["text_primary"])
    ax.set_xlabel("Task category", labelpad=58)
    ax.set_xticks([])
    ax.set_ylabel("Tokens per task (M)")
    ax.set_xlim(-0.56, n - 0.44)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"],
            zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in style["axes"]["spines"]:
        ax.spines[side].set_color(style["text_secondary"])
    # Headroom for the legend, which sits inside.
    # Fixed 0-3M in half-millions: a shared scale across the three model
    # panels, so a bar's height means the same thing in each.
    figtools.set_ticks(ax, 3.0, 6, step=0.5)
    if tallest > 3.0:
        print(f"  note: tallest stack is {tallest:.2f}M, above the 3M axis")

    # Two keys, one per encoding: colour says outcome, texture says arm.
    # Six combined entries would imply six independent series.
    # Colour is the only encoding left to explain: the arm and mode are read
    # off the axis rows beneath each bar.
    keys = [Patch(facecolor=c, edgecolor=style["surface"], label=lab)
            for _, c, lab in OUTCOME]
    # What the axis letters mean. Drawn as invisible handles so they read as
    # a key to the axis rather than as two more series.
    keys += [Patch(facecolor="none", edgecolor="none", label="f: fresh"),
             Patch(facecolor="none", edgecolor="none", label="r: reused")]
    ax.legend(handles=keys, frameon=False,
              fontsize=plt.rcParams["legend.fontsize"], handlelength=1.6,
              ncol=4, loc="upper left", bbox_to_anchor=(0.0, 1.0),
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
    ap.add_argument("--models", nargs="*", default=figtools.MODELS,
                    help="one FIGURE per model, lettered a, b, c")
    ap.add_argument("--out", type=Path, default=HERE / "eval4_tokens")
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
