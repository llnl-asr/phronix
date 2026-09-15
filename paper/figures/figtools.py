#!/usr/bin/env python3
"""Axis helpers shared by every figure in the paper.

The rule these enforce: when a figure carries a second y-axis, both axes get
the SAME number of major ticks. Otherwise the two sets of gridlines interleave
at unrelated heights and the plot grows a moire of horizontal rules that mean
nothing -- and worse, a reader can mistake a left-axis gridline for a level on
the right-hand scale. Equal counts make the two scales share one set of
horizontal rules.
"""
from __future__ import annotations

import math

from matplotlib.ticker import AutoMinorLocator, MultipleLocator

# Step sizes a reader can count in. Denser than the usual 1/2/5 decade set,
# because forcing a fixed number of intervals onto real data otherwise lands
# on a step that leaves half the canvas empty (2,695 entries in five steps
# wants 600, not 1,000).
NICE = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)


def nice_step(vmax: float, intervals: int) -> float:
    """Smallest countable step whose `intervals` steps cover `vmax`."""
    if vmax <= 0:
        return 1.0
    raw = vmax / intervals
    decade = 10.0 ** math.floor(math.log10(raw))
    for mult in NICE:
        step = mult * decade
        if step >= raw - 1e-12:
            return step
    return 10.0 * decade


def set_ticks(ax, vmax: float, intervals: int, *, minor: int = 2,
              step: float | None = None) -> float:
    """Put `intervals` equal major ticks on ax's y, starting at zero.

    Returns the step used. Pass `step` to pin it (a percentage axis wants 20s,
    not whatever the data suggests).
    """
    step = step if step is not None else nice_step(vmax, intervals)
    ax.set_ylim(0, step * intervals)
    ax.yaxis.set_major_locator(MultipleLocator(step))
    if minor:
        # Minor ticks subdivide the majors, so they stay meaningful whatever
        # the step turns out to be.
        ax.yaxis.set_minor_locator(AutoMinorLocator(minor))
        # Matplotlib's default minor tick is 2pt and invisible next to 18pt
        # type; give it enough length to read as a subdivision.
        ax.tick_params(axis="y", which="minor", length=4.0, width=1.0,
                       color=ax.yaxis.get_major_ticks()[0].tick1line.get_color()
                       if ax.yaxis.get_major_ticks() else None)
        ax.tick_params(axis="y", which="major", length=6.0)
    return step


def pair_axes(ax, ax2, left_max: float, right_max: float, *,
              intervals: int = 5, left_step: float | None = None,
              right_step: float | None = None, minor: int = 2) -> None:
    """Give a plot and its twin the same number of major y ticks."""
    set_ticks(ax, left_max, intervals, minor=minor, step=left_step)
    # Minor ticks on the twin as well would double the marks along the right
    # spine for no added precision; the left axis carries them.
    set_ticks(ax2, right_max, intervals, minor=0, step=right_step)


# ---------------------------------------------------------------------------
# Repeats
# ---------------------------------------------------------------------------
#
# Every figure in this paper is now a mean over repeated runs, drawn with the
# spread across those runs. One run of a stochastic agent is an anecdote: the
# same condition re-run moves by enough that a difference between two bars is
# unreadable without knowing how much either bar wanders on its own.
#
# The rule these helpers enforce is that n is never hidden. A single run gets
# NO error bar rather than a zero-length one -- a zero-length bar asserts a
# measurement of perfect stability, which is the opposite of what one run
# says -- and the caption reports n so the reader can tell the two apart.

def agg(rows: list[dict], key, field: str) -> dict:
    """Group `rows` by `key`, and reduce `field` to (mean, sd, n) per group.

    `sd` is the SAMPLE standard deviation (n-1), the estimate of the spread of
    the underlying condition rather than of the runs that happen to be in
    hand. It is None when n < 2, which is what makes "no error bar" distinct
    from "an error bar of zero".
    """
    from collections import defaultdict
    import statistics

    buckets: dict = defaultdict(list)
    for row in rows:
        try:
            buckets[key(row)].append(float(row[field] or 0))
        except (TypeError, ValueError):
            continue
    out = {}
    for group, values in buckets.items():
        mean = sum(values) / len(values) if values else 0.0
        sd = statistics.stdev(values) if len(values) > 1 else None
        out[group] = (mean, sd, len(values))
    return out


def errorbars(values: list) -> list | None:
    """Turn a list of (mean, sd, n) into matplotlib `yerr`, or None.

    None when NO group has more than one run, so the call site can omit the
    error bars entirely instead of drawing a row of zeros.
    """
    if not any(v[1] for v in values):
        return None
    return [v[1] or 0.0 for v in values]


def errorbars_at(means: list, values: list) -> list | None:
    """`yerr` as [lower, upper], with the lower arm never crossing zero.

    Every quantity these figures plot is a count or a mean of counts, so none
    of them can be negative -- yet a symmetric mean +/- sd draws through the
    axis whenever the spread is wider than the mean, which happens easily at
    1.2 attempts with an sd of 1.5. A whisker reaching -0.3 attempts is not a
    wider interval, it is an impossible one, and it makes the reader distrust
    the bar it hangs off.

    So the lower arm is truncated at the value itself and the upper arm is
    left alone: the interval still shows the full spread upward and stops
    where the quantity stops being defined.
    """
    if not any(v[1] for v in values):
        return None
    lower = [min(v[1] or 0.0, m) for m, v in zip(means, values)]
    upper = [v[1] or 0.0 for v in values]
    return [lower, upper]


def n_note(values: list) -> str:
    """`n=5` when every group has five runs, `n=1-5` when they differ.

    Written onto the figure rather than left to the caption: a reader
    comparing two panels must be able to see that one is an average of five
    runs and the other of one.
    """
    counts = sorted({int(v[2]) for v in values if v[2]})
    if not counts:
        return ""
    if len(counts) == 1:
        return f"n={counts[0]}"
    return f"n={counts[0]}-{counts[-1]}"


#: The models the paper reports, in the order the panels are lettered.
#: One figure per model, named `<stem>a.pdf`, `<stem>b.pdf`, `<stem>c.pdf`.
MODELS = ["gpt-5.4", "gpt-5.5", "gpt-5.6-sol"]

#: Panel letters, in model order.
LETTERS = "abcdefgh"


def panel_out(out: Path, index: int) -> Path:
    """`eval1_capabilities` + slot 1 -> `eval1_capabilitiesb.pdf`.

    A letter rather than the model name, because the letters are what the
    prose cites ("figure 1b") and a model rename must not break those
    references.
    """
    return out.with_name(f"{out.name}{LETTERS[index]}.pdf")


# ---------------------------------------------------------------------------
# Category order
# ---------------------------------------------------------------------------
#
# Alphabetical, and the same in every figure. Each plot used to rank
# categories by its own busiest measure -- eval 1 by capability volume, eval 3
# by tasks attempted, eval 4 by attempt count -- which put `django` first in
# one figure and third in another, and quietly made the six categories a
# `--top-n` kept differ between them too.
#
# Alphabetical rather than ranked by anything measured: a reader looking for
# `astropy` should find it in the same column in figures 1, 3 and 4 without
# first working out what that figure happens to sort by, and the order must
# not move when the data does.


#: Not a task category -- the fallback bucket `category_of` charges a
#: capability to when its filename names no repository (`apply_patch.py`, and
#: everything filed under `authoring`). It holds 123 tools and ZERO tasks, so
#: it can never carry a first-try rate, and on an alphabetical axis it sorted
#: into the top six and took a column from `scikit-learn` and `sympy`, which
#: have three tasks each. Kept in the CSV so the capability totals reconcile;
#: kept off the axis because a column no task can populate is not a category.
NOT_A_CATEGORY = {"general"}


def order_categories(cats) -> list:
    """Alphabetical by the name the axis shows -- the repo, not the owner.

    Sorted on the part after the slash, because that is what `short()` puts on
    the axis: `mwaskom/seaborn` reads as `seaborn` and belongs under S, not M.
    """
    return sorted({c for c in cats if c not in NOT_A_CATEGORY},
                  key=lambda c: (c.split("/")[-1].lower(), c.lower()))


#: How many tasks the benchmark's list contributes per repository. This is
#: what decides which categories a `--top-n` keeps -- the same six in every
#: figure, because it is a property of the task list rather than of anything a
#: figure measures.
#:
#: Ranking per figure was not enough. With each plot choosing its own busiest
#: six, figure 1 showed astropy and figure 3 showed flask instead: same order,
#: different cast, so the columns still did not line up across the paper.
TASKS_PER_CATEGORY = {
    "django/django": 5,
    "matplotlib/matplotlib": 3,
    "scikit-learn/scikit-learn": 3,
    "sympy/sympy": 3,
    "astropy/astropy": 2,
    "mwaskom/seaborn": 2,
    "pallets/flask": 2,
    "psf/requests": 2,
    "pydata/xarray": 2,
    "pylint-dev/pylint": 2,
    "pytest-dev/pytest": 2,
    "sphinx-doc/sphinx": 2,
}


def top_categories(available, top_n=None) -> list:
    """The `top_n` categories the benchmark weights most, in reading order.

    Two separate decisions, and collapsing them was the bug twice over. WHICH
    categories appear must be the same in every figure or the columns cannot
    be compared; WHERE they appear should be stable and obvious. So selection
    comes from the task list and display is alphabetical, and neither depends
    on what any particular figure happens to count.

    `available` is whatever that figure actually has data for; a category the
    task list weights highly but this figure never saw is not invented.
    """
    have = {c for c in available if c not in NOT_A_CATEGORY}
    ranked = sorted(have, key=lambda c: (-TASKS_PER_CATEGORY.get(c, 0),
                                         c.split("/")[-1].lower()))
    if top_n:
        ranked = ranked[:top_n]
    return order_categories(ranked)


#: Axis labels that do not fit beside their neighbours.
#:
#: `matplotlib` and `scikit-learn` are adjacent in the alphabetical order and
#: together overrun their two slots at 14pt, so the two names run into each
#: other on every figure. Abbreviated to the form the project itself uses --
#: `sklearn` is what the import is called -- rather than rotating the labels,
#: which costs vertical space on all six.
SHORT_NAMES = {
    "scikit-learn": "sklearn",
    "sphinx-doc": "sphinx",
    "pylint-dev": "pylint",
    "pytest-dev": "pytest",
}


def short_name(category: str) -> str:
    """`scikit-learn/scikit-learn` -> `sklearn`; keep the axis readable."""
    leaf = str(category).split("/")[-1]
    return SHORT_NAMES.get(leaf, leaf)
