"""Per-task records and the learning-rate computation.

This module is deliberately pure: it takes a list of task results and produces
numbers. No containers, no network, no harness. That keeps the part of the
benchmark most likely to be *wrong in an interesting way* — the statistics —
directly testable, and separable from the plumbing that merely has to work.

The headline is the learning rate, which is two numbers rather than one because
either alone is misleading:

``resolve_slope``
    Ordinary-least-squares slope of ``resolved`` (0/1) against task index. Says
    performance improved over the run.

``reuse_rate``
    Fraction of tasks that retrieved a skill written by an *earlier* task. Says
    the improvement is attributable to learning rather than to easier tasks
    happening to land later in the fixed order.

A positive slope with a zero reuse rate is not learning; it is ordering luck, and
reporting it as learning would be the benchmark lying about the thing it exists
to check.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class Attempt:
    """One independent attempt at a task, from a clean container."""

    index: int
    resolved: bool = False
    steps: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cache: int = 0
    cost_usd: float = 0.0
    wall_s: float = 0.0
    error: str = ""
    #: The earlier attempt this one re-applied, or 0. A retry that repeats a
    #: failed edit spends the budget believing the idea is still untested, and
    #: three such attempts read as three independent failures in the results.
    repeats_attempt: int = 0
    #: How the failure moved. "" when this is the first attempt, "moved" when it
    #: failed differently from the last one, "same" when it failed identically.
    #: Reported because a task that keeps failing differently is converging and
    #: one that repeats itself is not, and the results cannot show that
    #: difference from pass/fail alone.
    failure_trend: str = ""
    #: Consecutive attempts that failed with this same signature.
    same_failure_count: int = 0
    #: One entry per plan tried in parallel: which plan, how many target tests
    #: it made pass, and whether it solved the task. Reported because "plan B
    #: got two of three where the top-ranked plan got none" is the finding, and
    #: a single adopted patch hides it.
    trials: List[Dict[str, Any]] = field(default_factory=list)
    #: The skill holding the solution this attempt produced.
    #:
    #: Recorded because it is the thing somebody wants to OPEN. The result says
    #: a task passed; this says where the fix that passed it was written down,
    #: which is what the next task on the subject retrieves and what a reader
    #: checking the work has to find by hand otherwise.
    solution_skill: str = ""
    #: Tokens the learning pass spent after this attempt was judged.
    tokens_learn: int = 0
    #: Seconds the learning pass took. Separate from ``wall_s`` for the same
    #: reason the tokens are: it is a real cost of the arm, and it is not the
    #: agent solving the task. Folding them together hides which one is slow.
    learn_s: float = 0.0
    #: Seconds the research pass before this attempt took, revision included.
    #: Research runs inside the attempt's wall clock because it needs the
    #: exported checkout, so ``wall_s`` alone reports a six-step attempt as
    #: having taken seventeen minutes when sixteen of them were research.
    research_s: float = 0.0
    #: Dollars the research pass cost, revision included. Kept apart from
    #: ``cost_usd`` — which is the solve agent alone — because "phronix costs
    #: more" and "phronix's RESEARCH costs more" are different claims, and only
    #: the split says whether the research bought anything for its money.
    research_cost_usd: float = 0.0

    @property
    def cost_total_usd(self) -> float:
        """Everything this attempt cost the account: solve, research, learning."""
        return self.cost_usd + self.research_cost_usd

    @property
    def solve_s(self) -> float:
        """Seconds the agent spent on the TASK: no research, no learning.

        The number to compare against a baseline attempt, which has neither.
        """
        return max(0.0, self.wall_s - self.research_s - self.learn_s)

    #: The evaluation result, kept so the next attempt can be told what failed.
    #: Not serialised into the headline metrics; it is feedback, not a score.
    verdict: Optional[Dict[str, Any]] = field(default=None, repr=False)

    @property
    def tokens_total(self) -> int:
        """What the agent spent SOLVING. Learning is tracked separately."""
        return self.tokens_input + self.tokens_output + self.tokens_cache


@dataclass
class TaskResult:
    """Everything measured for one benchmark instance, across all its attempts."""

    instance_id: str
    repo: str = ""
    arm: str = ""
    order: int = 0                      # position in the fixed task order
    attempts: List[Attempt] = field(default_factory=list)

    #: Skills/lessons written during this task, by name.
    skills_created: List[str] = field(default_factory=list)
    #: Skills retrieved during this task, by name — including ones created here.
    skills_retrieved: List[str] = field(default_factory=list)
    #: Retrieved skills that were created by an EARLIER task. The learning signal.
    skills_reused: List[str] = field(default_factory=list)
    #: Of those, the ones created while working on a DIFFERENT repository.
    skills_reused_cross_repo: List[str] = field(default_factory=list)

    #: What the research pass did, when one ran: tools called, tokens, verdict.
    #: Its tokens are added to the task total below — research is part of the
    #: cost of the arm, and hiding it would make phronix look cheaper than it is.
    research: Dict[str, Any] = field(default_factory=dict)

    #: Files this task promoted into the durable project layer, by relative
    #: path. Recorded so "the store grew" can be traced to the task that grew it.
    promoted: List[str] = field(default_factory=list)

    #: Why an unresolved task stopped retrying, in until-pass mode. Recorded
    #: because "did not pass in 8 attempts" and "stopped repeating itself after
    #: 3" are different results, and a bare unresolved flag hides which happened.
    stopped_early: str = ""

    @property
    def resolved(self) -> bool:
        return any(a.resolved for a in self.attempts)

    @property
    def resolved_first_attempt(self) -> bool:
        """Resolved on the FIRST attempt — the like-for-like number across arms.

        Retry budgets differ deliberately: a memoryless baseline gets one attempt
        because extra ones only resample, while the phronix arms retry to the
        full budget because retrying-with-memory is the capability under test.
        That makes overall resolve rate an unequal comparison, so the report
        carries this alongside it. "Solved in three tries" against "failed in
        one" is not evidence of learning by itself.
        """
        return bool(self.attempts) and bool(self.attempts[0].resolved)

    @property
    def tries(self) -> int:
        """Attempts made. Equals attempts-until-pass when resolved, else the cap."""
        return len(self.attempts)

    @property
    def steps(self) -> int:
        return sum(a.steps for a in self.attempts)

    @property
    def tokens_solve(self) -> int:
        """Tokens spent attempting the task itself."""
        return sum(a.tokens_total for a in self.attempts)

    @property
    def tokens_learn(self) -> int:
        """Tokens spent turning attempts into stored knowledge."""
        return sum(a.tokens_learn for a in self.attempts)

    @property
    def tokens_research(self) -> int:
        """Tokens spent working out how the task should be approached.

        Every research pass for this task, initial and revisions. Reported apart
        from solving because it is the cost of the framework's distinctive step,
        and the only way to judge whether that step pays for itself is to see it
        on its own.
        """
        passes = self.research.get("passes_detail") if self.research else None
        if passes:
            return sum(int(p.get("tokens_input") or 0)
                       + int(p.get("tokens_output") or 0)
                       + int(p.get("tokens_cache") or 0) for p in passes)
        research = self.research or {}
        return (int(research.get("tokens_input") or 0)
                + int(research.get("tokens_output") or 0)
                + int(research.get("tokens_cache") or 0))

    @property
    def tokens_total(self) -> int:
        """Everything this task cost, across all three activities."""
        return self.tokens_solve + self.tokens_learn + self.tokens_research

    @property
    def cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.attempts)

    @property
    def wall_s(self) -> float:
        return sum(a.wall_s for a in self.attempts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{k: v for k, v in asdict(self).items() if k != "attempts"},
            "attempts": [asdict(a) for a in self.attempts],
            "resolved": self.resolved,
            "tries": self.tries,
            "steps": self.steps,
            "tokens_total": self.tokens_total,
            "tokens_solve": self.tokens_solve,
            "tokens_learn": self.tokens_learn,
            "tokens_research": self.tokens_research,
            "cost_usd": round(self.cost_usd, 6),
            "wall_s": round(self.wall_s, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        attempts = [Attempt(**a) for a in data.get("attempts", [])]
        known = {f for f in cls.__dataclass_fields__ if f != "attempts"}
        return cls(attempts=attempts,
                   **{k: v for k, v in data.items() if k in known})


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def ols_slope(values: Sequence[float]) -> Tuple[float, float]:
    """Least-squares slope of *values* against their index, and its standard error.

    Returns ``(slope, stderr)``. The standard error is returned alongside because
    a slope fitted to 30 noisy binary outcomes without an interval is a number
    that will be quoted as if it were precise — and on this sample size it is
    routinely not distinguishable from zero.
    """
    n = len(values)
    if n < 3:
        return 0.0, float("inf")
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, float("inf")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, values)]
    if n <= 2:
        return slope, float("inf")
    residual_var = sum(r ** 2 for r in residuals) / (n - 2)
    stderr = math.sqrt(residual_var / sxx) if sxx > 0 else float("inf")
    return slope, stderr


def confidence_interval(slope: float, stderr: float, z: float = 1.96) -> Tuple[float, float]:
    """A normal-approximation CI. Wide intervals are the honest output here."""
    if not math.isfinite(stderr):
        return (float("-inf"), float("inf"))
    return (slope - z * stderr, slope + z * stderr)


def rolling(values: Sequence[float], window: int) -> List[Tuple[int, int, float]]:
    """Non-overlapping window means: ``[(start, end, mean), ...]``, 1-indexed."""
    out: List[Tuple[int, int, float]] = []
    for start in range(0, len(values), window):
        chunk = values[start:start + window]
        if chunk:
            out.append((start + 1, start + len(chunk), sum(chunk) / len(chunk)))
    return out


# ---------------------------------------------------------------------------
# Arm summary
# ---------------------------------------------------------------------------

def summarise_arm(results: Sequence[TaskResult], window: int = 10) -> Dict[str, Any]:
    """Aggregate one arm's task results into the reported metrics.

    Results are sorted by their position in the fixed task order, not by the
    order they happened to finish in — with any concurrency at all those differ,
    and a slope fitted to completion order measures scheduling, not learning.
    """
    ordered = sorted(results, key=lambda r: r.order)
    if not ordered:
        return {"tasks": 0}

    resolved = [1.0 if r.resolved else 0.0 for r in ordered]
    tries = [float(r.tries) for r in ordered]
    tokens = [float(r.tokens_total) for r in ordered]

    resolve_slope, resolve_se = ols_slope(resolved)
    tries_slope, _ = ols_slope(tries)
    tokens_slope, _ = ols_slope(tokens)

    reused = [r for r in ordered if r.skills_reused]
    cross_repo = [r for r in ordered if r.skills_reused_cross_repo]
    solved = [r for r in ordered if r.resolved]
    solved_at_1 = [r for r in ordered if r.resolved_first_attempt]

    return {
        "tasks": len(ordered),
        "resolved": len(solved),
        "resolve_rate": round(len(solved) / len(ordered), 4),
        # Reported next to the overall rate because retry budgets differ by arm
        # on purpose. Comparing "solved in three tries" with "failed in one" is
        # not evidence of learning; comparing first attempts is like-for-like.
        "resolved_first_attempt": len(solved_at_1),
        "resolve_rate_first_attempt": round(len(solved_at_1) / len(ordered), 4),
        "tries_mean": round(statistics.fmean(tries), 3),
        "tries_total": int(sum(tries)),
        "steps_total": sum(r.steps for r in ordered),
        "tokens_total": int(sum(tokens)),
        # Split three ways so "phronix used more tokens" can be answered with
        # WHERE. Research is the framework's distinctive cost and has to be
        # visible on its own to be judged at all.
        "tokens_solve": int(sum(r.tokens_solve for r in ordered)),
        "tokens_learn": int(sum(r.tokens_learn for r in ordered)),
        "tokens_research": int(sum(r.tokens_research for r in ordered)),
        # The comparison that survives the phronix arm's larger tool surface:
        # per-step tokens are structurally higher for it, per-solved-task is the
        # number that reflects whether the extra context earned its keep.
        "tokens_per_resolved": (int(sum(tokens) / len(solved)) if solved else None),
        "cost_usd": round(sum(r.cost_usd for r in ordered), 4),
        "cost_per_resolved": (round(sum(r.cost_usd for r in ordered) / len(solved), 4)
                              if solved else None),
        "wall_s": round(sum(r.wall_s for r in ordered), 1),
        "learning_rate": {
            "resolve_slope": round(resolve_slope, 5),
            "resolve_slope_ci95": [round(v, 5) for v in
                                   confidence_interval(resolve_slope, resolve_se)],
            "resolve_slope_significant": _excludes_zero(resolve_slope, resolve_se),
            "reuse_rate": round(len(reused) / len(ordered), 4),
            "reuse_rate_cross_repo": round(len(cross_repo) / len(ordered), 4),
            "tries_slope": round(tries_slope, 5),
            "tokens_slope": round(tokens_slope, 1),
            "skills_created": sum(len(r.skills_created) for r in ordered),
        },
        "curve": [
            {"tasks": f"{a}-{b}", "resolve": round(v, 3),
             "tries": round(t, 2), "tokens": int(k)}
            for (a, b, v), (_, _, t), (_, _, k) in zip(
                rolling(resolved, window), rolling(tries, window), rolling(tokens, window))
        ],
    }


def _excludes_zero(slope: float, stderr: float) -> bool:
    low, high = confidence_interval(slope, stderr)
    return low > 0 or high < 0


def compare(summaries: Dict[str, Dict[str, Any]],
            learning_arm: str = "opencode-phronix",
            control_arm: str = "opencode-phronix-frozen") -> Dict[str, Any]:
    """Attribute any improvement to learning, or decline to.

    The learning arm's slope on its own proves nothing: the same fixed task order
    is shared by every arm, so easy-tasks-late would lift all of them. What the
    claim needs is that the learning arm's slope *exceeds* the identical-scaffolding
    control's, and that skills were actually reused.

    Returns a verdict that is deliberately willing to say "not demonstrated".
    """
    learner = summaries.get(learning_arm)
    control = summaries.get(control_arm)
    if not learner:
        return {"verdict": "no_data", "note": f"arm {learning_arm!r} was not run"}

    learning = learner["learning_rate"]
    if not control:
        return {
            "verdict": "uncontrolled",
            "resolve_slope": learning["resolve_slope"],
            "reuse_rate": learning["reuse_rate"],
            "note": (f"the control arm {control_arm!r} was not run, so a positive slope "
                     "cannot be separated from task-ordering effects. Run it before "
                     "quoting a learning rate."),
        }

    delta = learning["resolve_slope"] - control["learning_rate"]["resolve_slope"]
    reused = learning["reuse_rate"] > 0

    if delta > 0 and reused and learning["resolve_slope_significant"]:
        verdict = "learning_demonstrated"
        note = ("The learning arm improved faster than the identical scaffolding with a "
                "frozen store, and skills from earlier tasks were actually retrieved.")
    elif delta > 0 and reused:
        verdict = "learning_suggested"
        note = ("The learning arm improved faster than the control and reused skills, but "
                "the slope's confidence interval includes zero — the sample is too small "
                "to call it. More tasks, or more seeds.")
    elif delta > 0:
        verdict = "improvement_unexplained"
        note = ("The learning arm improved faster than the control, but no skill written "
                "by an earlier task was ever retrieved — so the improvement is not "
                "attributable to learning. Check that the store is writable and that "
                "retrieval is actually being called.")
    else:
        verdict = "no_learning"
        note = ("The learning arm did not improve faster than the frozen control. On this "
                "task set, accumulating skills did not measurably help.")

    return {
        "verdict": verdict,
        "note": note,
        "resolve_slope_learning": learning["resolve_slope"],
        "resolve_slope_control": control["learning_rate"]["resolve_slope"],
        "slope_delta": round(delta, 5),
        "reuse_rate": learning["reuse_rate"],
        "reuse_rate_cross_repo": learning["reuse_rate_cross_repo"],
        "tokens_per_resolved": {
            arm: s.get("tokens_per_resolved") for arm, s in summaries.items()
        },
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_results(path: Path, results: Iterable[TaskResult]) -> Path:
    """Append-friendly JSONL, so a crashed run keeps everything up to the crash."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.to_dict()) + "\n")
    return path


def append_result(path: Path, result: TaskResult) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict()) + "\n")


def read_results(path: Path) -> List[TaskResult]:
    path = Path(path)
    if not path.is_file():
        return []
    out: List[TaskResult] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(TaskResult.from_dict(json.loads(line)))
    return out
