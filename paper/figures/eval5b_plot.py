#!/usr/bin/env python3
"""Eval 5b -- was the work actually done correctly, stage by stage.

Eval 5 counts effort. Effort is not quality: a run can call four hundred tools
and still hand back a binary that never traces anything. This scores the
OUTCOME of each stage against a fixed checklist -- was the right toolchain
found, was the requested configuration honoured, do the annotations compile,
is the instrumentation really linked, did the run produce what it was for.

Three outcomes, because two would hide the interesting one:

* **correct** -- right the first time.
* **correct after self-repair** -- wrong first, caught INSIDE the run by its
  own validation, then fixed AT SOURCE and re-verified. The repair outlives
  the run: the tool is less broken afterwards. Only an arm with its own
  checking can score this, so a bare run cannot -- it has no validation step
  to catch anything with.
* **workaround** -- got past the obstacle without fixing it: the application's
  own configure.ac edited to suit the available autoconf, the MPI stack
  swapped to dodge a link error. The step proceeds and nothing is repaired;
  the next run meets the same wall. This is the red family, because
  thoroughness is the thing being measured and a workaround is its opposite.
* **incorrect** -- still wrong when the run ended, whether or not anyone
  noticed. Both arms land here on the same check: each built an instrumented
  binary, ran it successfully, and emitted no trace.

Scored as a percentage so stages with different numbers of checks can be read
against each other. The per-stage check count is in `eval5b_quality.csv` and
printed by this script, but kept off the axis: it is provenance for the
rubric rather than something the figure is comparing.

The checklist is a RUBRIC, not a measurement: a human fixed the criteria, and
each row of eval5b_quality.csv carries the evidence that decided it, so a
reader can disagree with a specific line rather than the whole figure. An arm
that has not been run is `unscored` and draws nothing -- never zero, which
would read as "did everything wrong" instead of "was not measured".
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import yaml

import figtools

#: Colour is the outcome, as everywhere else in this paper: the reserved good
#: and critical steps. Self-repair is the good colour, hatched -- it ends
#: correct, and the texture says it did not start that way.
OUTCOMES = [
    ("pass", "#0ca30c", "", "Correct"),
    ("repaired", "#0ca30c", "///", "Correct after self-repair"),
    ("workaround", "#d03b3b", "///", "Workaround"),
    ("fail", "#d03b3b", "", "Incorrect"),
]

#: Baseline first, then what is being argued for -- the same order as
#: eval5a, so the two figures can be read side by side.
ARMS = ["bare", "phronix"]
STAGES = ["setup", "annotate", "smoke", "trace"]


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


def read_rubric(path: Path) -> dict:
    """(arm, stage) -> Counter of outcomes, ignoring unscored rows."""
    tally: dict = defaultdict(Counter)
    with path.open() as fh:
        for row in csv.DictReader(fh):
            outcome = row["outcome"].strip()
            if outcome == "unscored":
                continue
            if outcome not in {o for o, *_ in OUTCOMES}:
                raise SystemExit(
                    f"eval5b_plot: unknown outcome {outcome!r} for "
                    f"{row['arm']}/{row['stage']}/{row['check']!r}."
                )
            tally[(row["arm"], row["stage"])][outcome] += 1
    return tally


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="eval5b_quality.csv")
    ap.add_argument("--style", default="style.yaml")
    ap.add_argument("--out", default="rendered/eval5b_quality.pdf")
    ap.add_argument("--size", default="column",
                    choices=["wide", "column", "square"])
    args = ap.parse_args()

    style = load_style(Path(args.style))
    tally = read_rubric(Path(args.csv))
    n = len(STAGES)

    # Shorter than the shared canvas: this figure is four stacked bars on a
    # fixed 0-100% axis, so the vertical room the other figures need for a
    # wide value range is dead space here.
    width, height = style["dimensions"][args.size]
    fig, ax = plt.subplots(figsize=(width, height * 0.82))

    span = style["axes"]["bar_width"]
    width = span / 2.6
    gap = width * 0.22
    for ai, arm in enumerate(ARMS):
        offs = [i - (span + gap) / 2 + width * (ai + 0.5) + gap * ai
                for i in range(n)]
        bottom = [0.0] * n
        for outcome, colour, hatch, _label in OUTCOMES:
            vals = []
            for stage in STAGES:
                counts = tally.get((arm, stage), Counter())
                total = sum(counts.values())
                # An unrun arm has no bar at all. Zero would say the stage was
                # scored and got everything wrong.
                vals.append(100.0 * counts[outcome] / total if total else 0.0)
            ax.bar(offs, vals, width=width, bottom=bottom, color=colour,
                   hatch=hatch,
                   edgecolor=style["text_secondary"] if hatch else style["surface"],
                   linewidth=1.0, zorder=3)
            bottom = [b + v for b, v in zip(bottom, vals)]

    # Arm under its own bar, stage and check count under the pair. Without the
    # arm labels two adjacent bars of the same colours cannot be told apart.
    ax.set_xticks(range(n))
    ax.set_xticklabels(list(STAGES))
    ax.tick_params(axis="x", length=0, pad=22)
    # Clear of the two rows beneath the axis: the arm names sit under each
    # bar and the stage name under the pair, so the title has to start below
    # both rather than at the usual tick distance.
    ax.set_xlabel("Stage", labelpad=18)
    for i in range(n):
        for ai, arm in enumerate(ARMS):
            centre = i - (span + gap) / 2 + width * (ai + 0.5) + gap * ai
            ax.annotate(arm, xy=(centre, 0), xytext=(0, -6),
                        textcoords="offset points", ha="center", va="top",
                        fontsize=plt.rcParams["font.size"] - 6,
                        color=style["text_secondary"], annotation_clip=False)

    ax.set_ylabel("Checks passed (%)")
    figtools.set_ticks(ax, 100, 5, minor=2)
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.5, n - 0.5)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"])
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    keys = [Patch(facecolor=c, hatch=h,
                  edgecolor=style["text_secondary"] if h else c, label=lab)
            for _o, c, h, lab in OUTCOMES]
    ax.legend(handles=keys, loc="lower left", bbox_to_anchor=(-0.02, 1.0),
              ncol=2, frameon=False, handlelength=1.4, columnspacing=1.0,
              labelspacing=0.3, borderpad=0.0, handletextpad=0.5)

    fig.tight_layout()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.02)
    print(f"wrote {out}")

    for arm in ARMS:
        for stage in STAGES:
            counts = tally.get((arm, stage), Counter())
            total = sum(counts.values())
            if not total:
                print(f"  {arm:<8} {stage:<9} unscored")
                continue
            print(f"  {arm:<8} {stage:<9} "
                  f"correct={counts['pass']} repaired={counts['repaired']} "
                  f"incorrect={counts['fail']}  n={total}")


if __name__ == "__main__":
    main()
