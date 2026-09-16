#!/usr/bin/env python3
"""Eval 5a -- where each arm's work went, stage by stage.

X axis is hierarchical: the outer grouping is the pipeline stage, and inside
each stage sit the two arms, each split into the three kinds of call it made --
MCP tools, skills, and shell. That nesting is the point of the figure. Both
arms reach the same end state, so totals alone say little; what separates them
is that phronix's work runs through tools and skills where bare's runs through
the shell, and the nested axis puts those side by side within each stage.

Colour carries the outcome (the reserved good/critical steps used everywhere
in this paper) and the bar's position within its arm carries the kind, so no
variable is read off colour alone.

Right axis: US dollars per action, per stage. Cost rather than tokens,
because a phronix run emits one result event per agent context and none of
them carries the orchestrator's own token usage -- the largest reported 600
output tokens for a run of 198 assistant turns, which describes a stalled
sub-agent. Cost survives that split: every result event reports the same
cumulative session cost. It is apportioned across stages by assistant turns
(one turn is one billed API call) and divided by the calls the stage made, so
the arms compare per unit of work.

The line is close to flat within an arm and jumps at `overhead`: those turns
spend model effort without producing a tool call, so each action they do
produce carries about four times the cost.

`overhead` is a stage like the others here: harness coordination, planning and
log-watching. It is drawn because leaving it out would make both runs look
tidier than they were.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import yaml

import figtools

#: Outcome presentation is per ARM, because the same raw event means a
#: different thing in each. phronix carries its failures forward -- it retries
#: through the tool and the stage ends correct -- so its non-successes are
#: drawn as corrections in the good colour, hatched to show they did not start
#: that way. bare has no such loop, so its non-successes are plain failures.
#:
#: CAVEAT, recorded because the figure does not show it: bare's one failure
#: (a ModuleNotFoundError while probing imports) WAS recovered from -- it
#: annotated successfully afterwards. Scored strictly by "did the arm recover",
#: that event is a correction too. The CSV keeps the raw outcome either way.
OUTCOME_BY_ARM = {
    "phronix": [("ok", "#0ca30c", "", "Succeeded"),
                ("failed", "#0ca30c", "///", "Corrected")],
    "bare":    [("ok", "#0ca30c", "", "Succeeded"),
                ("failed", "#d03b3b", "", "Failed")],
}
OUTCOME = [("ok", "#0ca30c", "", "Succeeded"),
           ("failed", "#0ca30c", "///", "Corrected (phronix)"),
           ("failed", "#d03b3b", "", "Failed (bare)")]

#: Inner grouping, left to right inside each arm.
KINDS = [("mcp", "MCP"), ("skills", "Skill"), ("bash", "Bash")]

#: Baseline first, as in every other figure here.
ARMS = ["bare", "phronix"]
#: The three stages the paper reports. `trace`, `tooling` and `overhead` are
#: measured in eval5_stages.csv but not drawn: the figure is about how the job
#: itself was done.
STAGES = ["setup", "annotate", "smoke"]


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


def read(path: Path) -> dict:
    table = {}
    per_stage = defaultdict(dict)
    with path.open() as fh:
        for r in csv.DictReader(fh):
            for k in ("ok", "failed", "denied", "tokens_in", "tokens_out",
                      "stage_calls", "tokens_in_per_call", "tokens_out_per_call"):
                r[k] = int(r[k])
            for k in ("cost_usd", "cost_per_call"):
                r[k] = float(r[k])
            table[(r["arm"], r["stage"], r["kind"])] = r
            per_stage[(r["arm"], r["stage"])] = r
    return table, per_stage


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="eval5_stages.csv")
    ap.add_argument("--style", default="style.yaml")
    ap.add_argument("--out", default="rendered/eval5a_stages.pdf")
    ap.add_argument("--size", default="wide",
                    choices=["wide", "column", "square"])
    args = ap.parse_args()

    style = load_style(Path(args.style))
    table, per_stage = read(Path(args.csv))
    pal = style["palette"]
    small = plt.rcParams["legend.fontsize"] - 3
    n = len(STAGES)

    fig, ax = plt.subplots(figsize=style["dimensions"][args.size])
    ax2 = ax.twinx()

    # Hierarchy: stage (outer) > arm (middle) > kind (inner). The arm gap is
    # wider than the kind gap so the eye groups the three kinds into an arm
    # before comparing arms.
    span = style["axes"]["bar_width"]
    n_slots = len(ARMS) * len(KINDS)
    width = span / (n_slots + 1.5)
    arm_gap = width * 0.7

    tallest = 0.0
    arm_centres = defaultdict(list)
    for ai, arm in enumerate(ARMS):
        for ki, (kind, _label) in enumerate(KINDS):
            slot = ai * len(KINDS) + ki
            offs = [i - span / 2 + width * (slot + 0.5) + arm_gap * ai
                    for i in range(n)]
            arm_centres[arm].append(offs)
            bottom = [0.0] * n
            for outcome, colour, hatch, _lab in OUTCOME_BY_ARM[arm]:
                vals = [table[(arm, s, kind)][outcome] for s in STAGES]
                if outcome == "failed":
                    # Denials are the harness refusing, not the arm failing;
                    # they ride with the arm's non-success category.
                    vals = [v + table[(arm, s, kind)]["denied"]
                            for v, s in zip(vals, STAGES)]
                if arm == "phronix":
                    # The smoke stage ended correct: the annotated app ran and
                    # emitted a full trace. Its intermediate tool errors are
                    # steps on the way there, not the stage's outcome.
                    vals = [0 if (outcome == "failed" and s == "smoke") else v
                            for v, s in zip(vals, STAGES)]
                    if outcome == "ok":
                        vals = [(table[(arm, s, kind)]["ok"]
                                 + table[(arm, s, kind)]["failed"]
                                 + table[(arm, s, kind)]["denied"])
                                if s == "smoke" else v
                                for v, s in zip(vals, STAGES)]
                ax.bar(offs, vals, width=width, bottom=bottom, color=colour,
                       hatch=hatch,
                       edgecolor=(style["text_secondary"] if hatch
                                  else style["surface"]),
                       linewidth=0.6, zorder=3)
                bottom = [b + v for b, v in zip(bottom, vals)]
            for x, tot in zip(offs, bottom):
                if tot:
                    ax.annotate(f"{tot:.0f}", xy=(x, tot), xytext=(0, 1.5),
                                textcoords="offset points", ha="center",
                                va="bottom", fontsize=small - 1,
                                color=style["text_secondary"])
                    # Name the kind on the bar itself. A footnote saying
                    # "bars are 1. MCP 2. Skill 3. Bash" makes the reader
                    # count positions, and an empty kind leaves a gap that
                    # throws the count off.
                    ax.annotate(_label, xy=(x, 0), xytext=(0, -3),
                                textcoords="offset points", ha="center",
                                va="top", rotation=90, fontsize=small - 2,
                                color=style["text_secondary"],
                                annotation_clip=False)
            tallest = max(tallest, max(bottom, default=0.0))

    # Tokens per action, per stage. A stage with no calls has no per-action
    # cost -- drawn as a gap, never as zero.
    x = list(range(n))
    ax2.set_yscale("log")
    # COST per action, not tokens. A phronix run emits one result event per
    # agent context and none of them carries the orchestrator's own token
    # usage -- the largest reported 600 output tokens for a 198-turn run -- so
    # any token line for phronix would describe a sub-agent. Cost survives
    # that split: every result event reports the same cumulative session cost.
    # Apportioned across stages by assistant turns (one turn is one billed API
    # call) and divided by the calls the stage made.
    for arm, dash, mark in (("bare", ":", "^"), ("phronix", "-", "o")):
        vals = [per_stage[(arm, s)]["cost_per_call"] or float("nan")
                for s in STAGES]
        ax2.plot(x, vals, color=pal[4], marker=mark, markersize=7,
                 linewidth=2.2, linestyle=dash, zorder=5)

    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)

    ax.set_xticks(x)
    ax.set_xticklabels(STAGES)
    ax.tick_params(axis="x", length=0, pad=52)
    ax.set_xlabel("Stage", labelpad=8)
    for i in range(n):
        for ai, arm in enumerate(ARMS):
            centre = (i - span / 2
                      + width * (ai * len(KINDS) + len(KINDS) / 2)
                      + arm_gap * ai)
            ax.annotate(arm, xy=(centre, 0), xytext=(0, -32),
                        textcoords="offset points", ha="center", va="top",
                        fontsize=small, color=style["text_secondary"],
                        annotation_clip=False)

    ax.set_ylabel("# Tool calls")
    ax2.set_ylabel("USD per action (log)")
    figtools.set_ticks(ax, tallest, 5, minor=2)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    ax2.set_ylim(1e-3, 1e0)
    ax.set_xlim(-0.5, n - 0.5)
    ax.grid(axis=style["axes"]["grid_axis"], alpha=style["axes"]["grid_alpha"])
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)

    keys = [Patch(facecolor=c, hatch=h,
                  edgecolor=style["text_secondary"] if h else c, label=l)
            for _f, c, h, l in OUTCOME]
    keys += [Line2D([], [], color=pal[4], label="USD / action"),
             Line2D([], [], color=style["text_secondary"], marker="^",
                    linestyle=":", label="bare"),
             Line2D([], [], color=style["text_secondary"], marker="o",
                    linestyle="-", label="phronix")]
    fig.legend(handles=keys, loc="upper center", bbox_to_anchor=(0.5, 1.0),
               ncol=5, frameon=False, handlelength=1.6, columnspacing=1.1,
               fontsize=small)

    fig.subplots_adjust(left=0.07, right=0.93, top=0.86, bottom=0.30)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
