#!/usr/bin/env python3
"""Eval 5 -- one agentic pipeline run, by phase, against a bare baseline.

Left axis, two stacked bars per arm: the capabilities the phase exercised,
split by outcome. Green succeeded, red failed -- the same reserved status
steps every other figure in this paper uses. Each bar stacks the two kinds of
capability, skills and MCP tools, told apart by hatch so the status colours
keep their one job.

Right axis, two lines: tokens PER ACTION, in and out. Raw totals are not a
fair comparison -- phronix annotated 418 regions across 29 files, bare
annotated 9 across 2, so naturally the larger job cost more. Dividing by the
tool calls the phase actually made asks the comparable question: what did one
unit of work cost?

Normalised, the output order reverses. Bare spends 377 output tokens per
action annotating against phronix's 114, because a bare run writes long shell
and edit blocks where the pipeline emits a compact tool call. Input per action
is close (73K bare, 79K phronix), which is the honest reading: the skill
context is not what makes phronix expensive.

The per-phase split is APPORTIONED, not read off the stream. Complete usage
appears only on the final result event -- per-message records are streaming
snapshots (output tops out at 34 tokens a message) and summing per-message
cache reads counts the same prefix once per turn, inflating input to 103.7M
against a true 40.2M. So the run's true totals are divided across phases by
measured activity: input by assistant turns, output by generated characters.
Phronix's smoke phase draws no line -- it runs inside the build step and has
no turns of its own, so a gap says "not separable" where a zero would claim
it was free.

Every tool call lands in exactly one of three kinds: MCP tools, skills, and
other (Bash, Read, Edit). "Other" is not a leftover bin -- it is how a bare
run does ALL of its work, and without it bare's bars are empty and the figure
reads as though bare did nothing. What the split actually shows is where the
work went: phronix drives 167 of its 239 annotate calls through MCP tools,
where bare's 41 calls are shell and edits end to end.

Bare is drawn first in each phase, phronix second: the baseline is what the
reader should meet before the thing being argued for.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import yaml

import figtools

#: Reserved status steps: good and critical. Success and failure are a status,
#: not two categories, and both always carry a written label.
OUTCOME = [
    ("ok", "#0ca30c", "Succeeded"),
    ("failed", "#d03b3b", "Failed"),
]

#: The two kinds of capability, told apart by texture so colour stays free to
#: mean outcome. MCP tools are the plain one; skills are marked.
KINDS = [
    ("tools", "", "MCP tools"),
    ("skills", "///", "Skills"),
    ("other", "...", "Other tools"),
]

#: Arms, left to right within each phase: the baseline first, then what is
#: being argued for, so a reader crosses the comparison in the order the claim
#: is made.
ARMS = ["bare", "phronix"]

PHASES = ["setup", "annotate", "build", "smoke"]


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


def read_rows(path: Path) -> dict:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    table = {}
    for r in rows:
        for k, v in r.items():
            if k not in ("arm", "phase"):
                r[k] = int(v)
        table[(r["arm"], r["phase"])] = r
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="eval5_phases.csv")
    ap.add_argument("--style", default="style.yaml")
    ap.add_argument("--out", default="rendered/eval5_pipeline.pdf")
    ap.add_argument("--size", default="column",
                    choices=["wide", "column", "square"])
    args = ap.parse_args()

    style = load_style(Path(args.style))
    table = read_rows(Path(args.csv))
    pal = style["palette"]
    n = len(PHASES)
    # Secondary annotations -- arm names and bar values -- one step below the
    # legend, which is itself one step below the base size. At tick size they
    # collide: "phronix" and "bare" run together under 8.5in of axis.
    small = plt.rcParams["legend.fontsize"] - 3

    # Broken left axis. One phase (annotate, 167 capabilities) is six times
    # the next, and on a single scale everything else is a stub two pixels
    # tall. The break at 30 gives the small phases their own readable panel.
    #
    # The RIGHT axis is broken at the matching place, so the token lines stay
    # continuous across the two panels instead of stopping at the seam: input
    # per action (~1e5) lives in the upper panel, output per action (~1e2-1e3)
    # in the lower one, and each line is drawn on both twins so whichever
    # panel holds it renders it.
    fig, (ax_hi, ax) = plt.subplots(
        2, 1, sharex=True, figsize=style["dimensions"][args.size],
        gridspec_kw={"height_ratios": [1, 1.3], "hspace": 0.06})
    ax2 = ax.twinx()
    ax2_hi = ax_hi.twinx()
    panels = ((ax, ax2), (ax_hi, ax2_hi))

    # Four bars per phase: two arms, each with a success and a failure stack.
    # Four bars a phase in two pairs. The gap between the pairs is wider than
    # the gap inside one, so the eye groups success+failure per arm rather than
    # reading four equally spaced bars and having to consult the labels.
    span = style["axes"]["bar_width"]
    width = span / 4.8
    gap = width * 0.55
    slots = []          # (arm, outcome) -> x offsets, in draw order
    for ai, arm in enumerate(ARMS):
        for oi, (outcome, _c, _l) in enumerate(OUTCOME):
            k = ai * 2 + oi
            off = width * (k + 0.5) + gap * ai
            slots.append((arm, outcome,
                          [i - (span + gap) / 2 + off for i in range(n)]))

    tallest = 0.0
    tops = []           # (x, total) for every bar, for the value labels
    for arm, outcome, offs in slots:
        bottom = [0.0] * n
        for kind, hatch, _lab in KINDS:
            field = f"{kind}_{outcome}"
            vals = [table[(arm, p)][field] for p in PHASES]
            colour = dict((o, c) for o, c, _ in OUTCOME)[outcome]
            for bar_ax, _ in panels:
                bar_ax.bar(offs, vals, width=width, bottom=bottom, color=colour,
                           hatch=hatch,
                           edgecolor=(style["text_secondary"] if hatch
                                      else style["surface"]),
                           linewidth=1.0, zorder=3)
            bottom = [b + v for b, v in zip(bottom, vals)]
        tops.extend(zip(offs, bottom))
        tallest = max(tallest, max(bottom, default=0.0))

    # Both arms get token lines. Colour says in-or-out, dash and marker say
    # which arm, so neither variable is read off colour alone.
    x = list(range(n))
    for _, tok_ax in panels:
        tok_ax.set_yscale("log")

    def series(arm: str, field: str) -> list:
        # Zero means "not separable here", not "free": drawn as a gap, which
        # a log axis has no way to misread.
        return [table[(arm, p)][field] or float("nan") for p in PHASES]

    for arm, dash, mark in (("phronix", "-", "o"), ("bare", ":", "^")):
        for _, tok_ax in panels:
            tok_ax.plot(x, series(arm, "tokens_in_per_call"), color=pal[0],
                        marker=mark, markersize=7, linewidth=2.5,
                        linestyle=dash, zorder=5)
            tok_ax.plot(x, series(arm, "tokens_out_per_call"), color=pal[4],
                        marker=mark, markersize=7, linewidth=2.5,
                        linestyle=dash, zorder=5)

    for bar_ax, tok_ax in panels:
        bar_ax.set_zorder(tok_ax.get_zorder() + 1)
        bar_ax.patch.set_visible(False)

    # Phase name under the pair of arms; arm name under its own two bars.
    ax.set_xticks(range(n))
    ax.set_xticklabels(PHASES)
    ax.tick_params(axis="x", length=0, pad=18)
    for i in range(n):
        for ai, arm in enumerate(ARMS):
            centre = i - (span + gap) / 2 + width * (ai * 2 + 1) + gap * ai
            ax.annotate(arm, xy=(centre, 0), xytext=(0, -6),
                        textcoords="offset points", ha="center", va="top",
                        fontsize=small,
                        color=style["text_secondary"], annotation_clip=False)

    # Break at 80: everything except annotate's 239 fits below it, including
    # phronix's 73-call setup and 75-call build, which a lower break would
    # have pushed across the seam and made unreadable in both panels.
    BREAK = 80
    # Upper limit from the data, not a constant: adding "other" to the stacks
    # took the tallest bar from 167 to 239, which a hardcoded 240 clipped flat
    # against the spine. Round up to the next 20 with ~8% headroom so the bar
    # reads as a bar rather than as a bar that ran out of axis.
    import math
    hi_top = 20 * math.ceil(tallest * 1.08 / 20)
    ax.set_ylim(0, BREAK)
    ax_hi.set_ylim(BREAK, hi_top)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax_hi.set_yticks(list(range(120, int(hi_top), 60)))
    if tallest >= hi_top:
        raise SystemExit(
            f"eval5_plot: tallest bar {tallest:.0f} does not fit under "
            f"{hi_top} -- the upper panel would clip it.")

    # Eight ticks a side: five below the break and three above, on both axes,
    # so no left-hand gridline can be mistaken for a level on the right.
    ax2.set_ylim(1e0, 1e4)
    ax2.set_yticks([1e0, 1e1, 1e2, 1e3, 1e4])
    ax2_hi.set_ylim(1e4, 1e7)
    ax2_hi.set_yticks([1e5, 1e6, 1e7])

    # Value above every bar that fits under the break. The small bars are the
    # reason the axis is broken at all; a reader should not have to measure
    # a 5-call bar against a gridline 20 units apart.
    for xpos, total in tops:
        if 0 < total < BREAK:
            ax.annotate(f"{total:.0f}", xy=(xpos, total), xytext=(0, 2),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=small,
                        color=style["text_secondary"])

    # One y label per side, centred on the pair rather than on either panel.
    # Sit the axis titles next to their tick labels. supylabel defaults to the
    # figure edge, which at this width leaves a visible gap between title and
    # numbers and reads as though it belongs to neither panel.
    fig.supylabel("# Tool calls", x=0.028,
                  fontsize=plt.rcParams["axes.labelsize"])
    fig.text(0.972, 0.56, "Tokens per action (log)", rotation=270,
             va="center", ha="left",
             fontsize=plt.rcParams["axes.labelsize"])

    # The arm names sit under the ticks, so the stage title clears both.
    ax.set_xlabel("Stage", labelpad=6)

    ax.set_xlim(-0.5, n - 0.5)
    for bar_ax in (ax, ax_hi):
        bar_ax.grid(axis=style["axes"]["grid_axis"],
                    alpha=style["axes"]["grid_alpha"])
        bar_ax.set_axisbelow(True)

    # The seam: no spine across the break, and a pair of diagonal ticks to say
    # the axis is cut rather than simply short.
    ax_hi.spines["bottom"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax_hi.spines["top"].set_visible(False)
    ax_hi.tick_params(axis="x", which="both", length=0)
    kw = dict(marker=[(-1, -0.6), (1, 0.6)], markersize=9, linestyle="none",
              color=style["text_secondary"], mec=style["text_secondary"],
              mew=1.2, clip_on=False)
    ax_hi.plot([0, 1], [0, 0], transform=ax_hi.transAxes, **kw)
    ax.plot([0, 1], [1, 1], transform=ax.transAxes, **kw)

    keys = [Patch(facecolor=c, label=l) for _f, c, l in OUTCOME]
    keys += [Patch(facecolor=style["surface"], hatch=h,
                   edgecolor=style["text_secondary"], label=l)
             for _k, h, l in KINDS if h]
    keys += [Line2D([], [], color=pal[0], label="Tokens in / action"),
             Line2D([], [], color=pal[4], label="Tokens out / action"),
             Line2D([], [], color=style["text_secondary"], marker="o",
                    linestyle="-", label="phronix"),
             Line2D([], [], color=style["text_secondary"], marker="^",
                    linestyle=":", label="bare")]
    # Figure-level legend above both panels: inside either one it would sit on
    # the bars (lower) or the token lines (upper), and there is no empty band
    # left once the axis is broken.
    fig.legend(handles=keys, loc="upper center", bbox_to_anchor=(0.49, 1.005),
               ncol=4, frameon=False, handlelength=1.6, columnspacing=1.1,
               fontsize=plt.rcParams["legend.fontsize"])

    # tight_layout cannot reason about the twinned broken panels and warns;
    # the gridspec above already fixes the spacing.
    fig.subplots_adjust(left=0.115, right=0.875, top=0.84, bottom=0.26)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
