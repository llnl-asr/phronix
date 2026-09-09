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
