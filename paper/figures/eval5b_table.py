#!/usr/bin/env python3
"""Eval 5b as a table -- the per-check quality difference, ready to paste.

Reads the same ``eval5b_quality.csv`` the figure reads, so the table and the
bars can never disagree. The figure shows the shape; the table names the
checks and says which way each one went, which is what a reader needs when
they want to argue with a specific line rather than the whole result.

Emits four formats, none hand-maintained:

* LaTeX (booktabs) for the paper.
* Markdown for notes and PRs.
* HTML for PowerPoint and Google Slides -- open it, select all, paste. It
  arrives as a real editable table with the colours intact, which a screenshot
  does not.
* TSV for Excel, if the table needs sorting or editing before it lands.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

STAGES = ["setup", "annotate", "build", "smoke"]
ARMS = ["bare", "phronix"]

#: How each outcome prints. The symbol carries the verdict so a reader
#: skimming the column sees the pattern without reading every cell.
MARK = {
    "pass": ("\\cmark", "OK", "\u2713", "#0ca30c"),
    "repaired": ("\\rmark", "OK (self-repair)", "\u2713 repaired", "#0ca30c"),
    "workaround": ("\\wmark", "workaround", "\u25cb workaround", "#d03b3b"),
    "fail": ("\\xmark", "WRONG", "\u2717", "#d03b3b"),
    "unscored": ("--", "--", "\u2014", "#52514e"),
}

PREAMBLE = r"""% Requires: \usepackage{booktabs}
% Symbols used below -- define once in your preamble:
% \newcommand{\cmark}{\ding{51}}              % correct
% \newcommand{\rmark}{\ding{51}$^{\dagger}$}  % correct after self-repair
% \newcommand{\wmark}{$\circ$}                % workaround
% \newcommand{\xmark}{\ding{55}}              % incorrect
"""


def read(path: Path):
    rows = defaultdict(list)
    with path.open() as fh:
        for r in csv.DictReader(fh):
            rows[(r["stage"], r["check"])].append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="eval5b_quality.csv")
    ap.add_argument("--tex", default="rendered/eval5b_quality.tex")
    ap.add_argument("--md", default="rendered/eval5b_quality.md")
    ap.add_argument("--html", default="rendered/eval5b_quality.html")
    ap.add_argument("--tsv", default="rendered/eval5b_quality.tsv")
    args = ap.parse_args()

    rows = read(Path(args.csv))

    # Keep the CSV's own order within a stage; it is the order the checks were
    # written and it reads as a sequence of things that had to go right.
    ordered = []
    seen = set()
    with open(args.csv) as fh:
        for r in csv.DictReader(fh):
            key = (r["stage"], r["check"])
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    ordered.sort(key=lambda k: STAGES.index(k[0]))

    def outcome(stage, check, arm):
        for r in rows[(stage, check)]:
            if r["arm"] == arm:
                return r["outcome"]
        return "unscored"

    tex = [PREAMBLE, r"\begin{tabular}{llcc}", r"\toprule",
           r"Stage & Check & Bare & Phronix \\", r"\midrule"]
    md = ["| Stage | Check | Bare | Phronix |", "|---|---|---|---|"]
    tsv = ["Stage\tCheck\tBare\tPhronix"]
    html = ['<table style="border-collapse:collapse;font-family:'
            'Calibri,Helvetica,Arial,sans-serif;font-size:16px">',
            '<tr style="background:#f0efec">'
            '<th style="text-align:left;padding:7px 12px;'
            'border-bottom:2px solid #333">Stage</th>'
            '<th style="text-align:left;padding:7px 12px;'
            'border-bottom:2px solid #333">Check</th>'
            '<th style="padding:7px 12px;border-bottom:2px solid #333">Bare</th>'
            '<th style="padding:7px 12px;border-bottom:2px solid #333">'
            'Phronix</th></tr>']

    last_stage = None
    for stage, check in ordered:
        b, p = (outcome(stage, check, a) for a in ARMS)
        stage_cell = stage if stage != last_stage else ""
        if stage != last_stage and last_stage is not None:
            tex.append(r"\addlinespace")
        last_stage = stage
        safe = check.replace("&", r"\&").replace("_", r"\_")
        tex.append(f"{stage_cell} & {safe} & {MARK[b][0]} & {MARK[p][0]} \\\\")
        md.append(f"| {stage_cell} | {check} | {MARK[b][1]} | {MARK[p][1]} |")
        tsv.append(f"{stage_cell}\t{check}\t{MARK[b][1]}\t{MARK[p][1]}")
        cell = ('padding:6px 12px;border-bottom:1px solid #ddd;'
                'text-align:center;white-space:nowrap')
        html.append(
            f'<tr><td style="padding:6px 12px;border-bottom:1px solid #ddd">'
            f'<b>{stage_cell}</b></td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #ddd">'
            f'{check}</td>'
            f'<td style="{cell};color:{MARK[b][3]}">{MARK[b][2]}</td>'
            f'<td style="{cell};color:{MARK[p][3]}">{MARK[p][2]}</td></tr>')

    # Totals: how many checks each arm got right, counting a self-repair as
    # right (it ends correct) and a workaround as not (it does not).
    def score(arm):
        good = sum(1 for s, c in ordered
                   if outcome(s, c, arm) in ("pass", "repaired"))
        return good, len(ordered)

    bg, bt = score("bare")
    pg, pt = score("phronix")
    tex += [r"\midrule",
            rf"\multicolumn{{2}}{{l}}{{\textbf{{Checks correct}}}} & "
            rf"\textbf{{{bg}/{bt}}} & \textbf{{{pg}/{pt}}} \\",
            r"\bottomrule", r"\end{tabular}"]
    md += [f"| **Total** | **checks correct** | **{bg}/{bt}** | **{pg}/{pt}** |"]
    tsv.append(f"Total\tchecks correct\t{bg}/{bt}\t{pg}/{pt}")
    tot = ('padding:8px 12px;border-top:2px solid #333;text-align:center;'
           'font-weight:bold')
    html += [f'<tr style="background:#f0efec">'
             f'<td colspan="2" style="padding:8px 12px;'
             f'border-top:2px solid #333;font-weight:bold">Checks correct</td>'
             f'<td style="{tot};color:#d03b3b">{bg}/{bt}</td>'
             f'<td style="{tot};color:#0ca30c">{pg}/{pt}</td></tr>',
             '</table>']

    for path, lines in ((args.tex, tex), (args.md, md),
                        (args.html, html), (args.tsv, tsv)):
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n")
        print(f"wrote {out}")

    print()
    print("\n".join(md))


if __name__ == "__main__":
    main()
