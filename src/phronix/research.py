"""Self-research: find out how a task should be done *before* attempting it.

The gap this fills is visible in a benchmark transcript. Given an unfamiliar bug,
an agent opens the file it first suspects, writes a plausible fix, fails, and
then — with a learning loop attached — writes down increasingly detailed notes
about the same wrong file. Three attempts, one location, and the correct fix a
single line away in a module nobody opened. Nothing in that loop ever asks *how
should this class of problem be approached*; every step assumes the approach and
refines the execution.

Research is the missing first step, and it runs only when the library does not
already cover the subject. Its output is deliberately not an answer: it is
**infrastructure**.

``assess``
    Does the catalogue already cover this? Deterministic, and the gate for
    everything below — researching a subject already understood is waste.

``add_approach`` / ``choose``
    Candidate approaches, each carrying *measured* numbers, and an argmax over
    them. The comparison is arithmetic, never a judgement call: a model asked to
    pick "the best approach" reliably picks the one it described most fluently.
    :func:`choose` refuses to answer when the numbers cannot support one —
    missing metrics, or a tie — rather than inventing a winner.

``write_plan``
    Splits the chosen approach into steps, each tagged ``deterministic`` or
    ``judgement``. That split is the whole point: a deterministic step becomes an
    MCP capability that runs the same way forever, and a judgement step becomes a
    skill block that guides without pretending to be mechanical. Prose describing
    a deterministic procedure is a procedure that will be done differently next
    time.

Records live in the write layer under ``research/`` so a plan is inspectable,
diffable and shareable with the repository, like every other thing phronix
learns.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Content directory for research records, alongside skills/ and memory/.
RESEARCH_DIR = "research"

#: A subject is considered covered when a skill search returns at least this many
#: blocks. One weak match is not coverage — it is the failure mode that made an
#: agent skip research on a subject it knew nothing about.
MIN_BLOCKS_FOR_COVERAGE = 2

#: Steps whose kind must be one of these. ``deterministic`` becomes a capability,
#: ``judgement`` becomes a skill block.
STEP_KINDS = ("deterministic", "judgement")

#: The three phases a self-authored task instance can belong to, and what each
#: one is *for*. The split is what separates "this handles the case I built it
#: against" from "this handles the behaviour".
#:
#: ``train``
#:    Discovery. These instances are how different approaches are found at all —
#:    poke the behaviour, see what governs it, derive candidates. Failing here
#:    means nothing; this is where the ideas come from.
#:
#: ``validate``
#:    Refinement and selection. Approaches are tuned against these and compared
#:    on them. An approach may be reworked as often as needed here — that is the
#:    phase's purpose — so failing validate does not kill an approach, it means
#:    it is not finished.
#:
#: ``test``
#:    Correctness, on instances the approach has never been shaped against.
#:    Touched once, at the end. **This is the only phase that falsifies.** An
#:    approach tuned until it passes its own tuning set has demonstrated nothing;
#:    the unseen set is the whole claim.
PHASES = ("train", "validate", "test")

#: Statuses an approach moves through. Only measurement moves it.
APPROACH_STATUSES = ("potential", "validated", "confirmed", "working",
                     "falsified")

#: Instances a corpus should hold before a split means anything.
#:
#: Three instances — one per phase — was the earlier design, and "confirmed on
#: the unseen set" then rested on a single probe that could pass by luck or by
#: resembling the tuning case. Confidence needs a corpus, and a corpus needs
#: enough cases that a split leaves real evidence in every part of it.
#:
#: A topic may declare a smaller target when the task genuinely cannot produce
#: this many distinct cases, but it must say why — see :func:`declare_corpus`.
DEFAULT_CORPUS_TARGET = 100

#: How the corpus is divided. Train is largest because discovery needs the most
#: material; test is held back and touched once.
DEFAULT_SPLIT = {"train": 0.6, "validate": 0.2, "test": 0.2}

#: Tuning is train + validate; only `test` decides. 80:20, and the 20 is never
#: seen until the final measurement.
TUNING_PHASES = ("train", "validate")

#: Below this, a held-out set is too small to mean anything.
#:
#: At twenty instances the unseen set is four cases. At ten it is two, and two
#: cases can be passed by accident — which then reads as `confirmed` and
#: licenses writing the approach up as knowledge. The floor is on the corpus
#: because that is where it can be acted on: the split cannot manufacture
#: evidence that was never collected.
MIN_CORPUS_INSTANCES = 20


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:80]


#: Session isolation. When set, this session's research is written to its own
#: folder and — unless reuse is on — reads see nothing but its own work.
SESSION_ENV = "PHRONIX_RESEARCH_SESSION"

#: Opt in to reading across every session plus the common folder.
REUSE_ENV = "PHRONIX_RESEARCH_REUSE"

#: Where per-session folders live, under the common research folder.
SESSIONS_DIR = "sessions"


def _research_home() -> Path:
    """The common research folder: the shared, checked-in one."""
    from phronix.layers import resolve_write_layer

    layer = resolve_write_layer()
    path = Path(layer.root) / RESEARCH_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _root() -> Path:
    """Where THIS session writes. Every read and write funnels through here.

    With a session set, records go to ``research/sessions/<id>/`` and stay there
    until the session is synced. That is what makes a run genuinely start from
    nothing: the isolation has to be at the storage layer, because a run that
    can see earlier research will use it, and then the run cannot answer the
    question it was set up to ask.

    Sessions are not checked in. :func:`sync_session` folds a finished session
    into the common folder, which is; so what gets committed is research that
    completed, not the working state of every run that ever started.
    """
    home = _research_home()
    session = os.environ.get(SESSION_ENV, "").strip()
    if not session:
        return home
    path = home / SESSIONS_DIR / _slug(session)
    path.mkdir(parents=True, exist_ok=True)
    return path


def reuse_enabled() -> bool:
    """Should reads gather across every session and the common folder?"""
    return os.environ.get(REUSE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _search_roots() -> List[Path]:
    """Every folder a READ may look in, nearest first.

    Without reuse this is the current session alone — the point of the session
    being that nothing else is visible. With reuse on it is the current session,
    then the common folder, then every other session: "look in all session
    folders" means exactly that, because a session that has not been synced yet
    still holds real findings, and the run that could use them is usually the
    one happening while it is still unsynced.

    Nearest first matters: the current session's version of a topic wins over an
    older one, so a record being actively written is never shadowed by a stale
    copy of itself.
    """
    home = _research_home()
    current = _root()
    if not reuse_enabled():
        return [current]

    roots = [current, home]
    sessions = home / SESSIONS_DIR
    if sessions.is_dir():
        try:
            roots += sorted((p for p in sessions.iterdir() if p.is_dir()),
                            key=lambda p: -p.stat().st_mtime)
        except OSError:
            pass

    seen, ordered = set(), []
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key not in seen:
            seen.add(key)
            ordered.append(root)
    return ordered


def _find_record(slug: str) -> Optional[Path]:
    """The nearest existing file for this slug across the search roots."""
    for root in _search_roots():
        candidate = root / f"{slug}.json"
        if candidate.is_file():
            return candidate
    return None


def _record_path(topic: str) -> Path:
    """Where a topic's record lives — one file per task when a topic is bound.

    The binding is applied here rather than in each public function because
    every read and write funnels through this one place, and the failure it
    prevents came from exactly the gap that a per-function check leaves: the
    readers resolved the topic, the writers did not, and one task ended up with
    three partial records under three agent-chosen names.
    """
    bound = os.environ.get(TOPIC_ENV, "").strip()
    slug = _slug(bound or topic)
    existing = _find_record(slug)
    return existing if existing is not None else _root() / f"{slug}.json"


def _write_path(topic: str) -> Path:
    """Where a WRITE goes: this session, always.

    Reads may reach into another session or the common folder; writes must not.
    A reusing run that saved through the read path edited the earlier session's
    record in place — so a finished run's history changed after the fact, with
    nothing recording that it had, and the isolation leaked backwards.

    Loading from elsewhere and saving here is the intended shape: the session
    starts from what it inherited and accumulates its own changes on top,
    leaving the source untouched.
    """
    bound = os.environ.get(TOPIC_ENV, "").strip()
    return _root() / f"{_slug(bound or topic)}.json"


#: When set, every research call is bound to this topic regardless of the key
#: passed in. The harness sets it per task.
TOPIC_ENV = "PHRONIX_RESEARCH_TOPIC"


def resolve_topic(hint: str) -> str:
    """The topic a caller means, tolerating a differently-worded key.

    **A bound topic wins outright.** When :data:`TOPIC_ENV` is set, that is the
    record, whatever string the caller passed. Agents name things descriptively
    and inconsistently, and three stages of one research pass produced three
    different keys for one task — the scope stage filed the figure of merit under
    ``pylint-recursive-ignore-paths``, the investigators filed approaches under
    ``pylint-7080-recursive-ignore-paths``, and the harness read
    ``pylint-dev__pylint-7080``. Every stage worked; nothing joined up, and the
    corrector reported an empty record while three partial ones sat on disk.

    Fuzzy resolution below is the fallback for unbound use, where a human or a
    single agent owns the naming.

    Agents name things descriptively. Told to file under
    ``pylint-dev__pylint-7080`` an agent will write
    ``pylint-recursive-ignore-paths`` instead, because that is what the subject
    is *about* — and it is not wrong, it is just not the key everything else
    looks under.

    Measured cost of not handling this: a research pass produced a figure of
    merit, two measured approaches and a four-step plan, and every later lookup
    found an empty record. The plan never reached the agent meant to follow it,
    the corrector reported "no figure of merit declared", and the attempt ledger
    accumulated under a third key nobody read. Everything worked and nothing
    connected.

    Exact match wins. Otherwise the most recently modified record that shares a
    meaningful word with the hint, which is enough because a run's store holds
    one task's records at a time.
    """
    def _has_research(stem: str) -> bool:
        record = load(stem)
        return bool(record.get("fom") or record.get("plan")
                    or record.get("chosen"))

    bound = os.environ.get(TOPIC_ENV, "").strip()
    if bound:
        return bound

    exact = _record_path(hint)
    if exact.is_file() and _has_research(_slug(hint)):
        return hint

    # An exact-named record that holds no research is usually the attempt ledger
    # opened under the harness's key, while the researcher filed its findings
    # under a descriptive name. Preferring the researched record is what makes
    # the two halves meet; falling back to the exact one keeps a run with no
    # research at all working unchanged.
    words = {w for w in re.split(r"[^a-z0-9]+", str(hint).lower())
             if len(w) > 3 and w not in ("test", "issue", "task")}
    candidates = []
    seen_stems = set()
    for root in _search_roots():
        try:
            paths = list(root.glob("*.json"))
        except OSError:
            continue
        for path in paths:
            stem = path.stem
            if stem in seen_stems:
                continue
            seen_stems.add(stem)
            shared = words & {w for w in re.split(r"[^a-z0-9]+", stem) if len(w) > 3}
            candidates.append((bool(shared), _has_research(stem),
                               path.stat().st_mtime, stem))
    if not candidates:
        return hint
    if not candidates:
        return hint
    candidates.sort(reverse=True)
    matched, researched, _, stem = candidates[0]
    return stem if (matched and researched) else hint


def load(topic: str) -> Dict[str, Any]:
    """The research record for *topic*, or an empty skeleton."""
    topic = os.environ.get(TOPIC_ENV, "").strip() or topic
    path = _record_path(topic)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"topic": topic, "slug": _slug(topic), "approaches": [],
            "plan": [], "chosen": None, "fom": None, "achieved": None}


def _save(record: Dict[str, Any]) -> Path:
    path = _write_path(record["topic"])
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. Is research needed at all?
# ---------------------------------------------------------------------------

def assess(task: str) -> Dict[str, Any]:
    """Whether the library already covers *task*, and therefore whether to research.

    Deterministic on purpose. "Do I already know this?" asked of a model is
    answered by its own confidence, which is exactly the signal that is wrong
    here — the agent that failed pylint-7080 three times was confident every
    time. Asked of the catalogue, it is a lookup.
    """
    from phronix import skills

    if not str(task).strip():
        return {"status": "error", "error": "task description is required"}

    found = skills.search(task)
    results = found.get("results", []) if isinstance(found, dict) else []
    blocks = sum(len(r.get("blocks") or []) for r in results)
    names = [r["skill"] for r in results]

    covered = blocks >= MIN_BLOCKS_FOR_COVERAGE
    return {
        "status": "ok",
        "task": task,
        "covered": covered,
        "matched_skills": names,
        "blocks": blocks,
        "verdict": "covered" if covered else "gap",
        "reason": (
            f"{blocks} block(s) across {len(names)} skill(s) already cover this; "
            "load them and proceed."
            if covered else
            f"only {blocks} matching block(s) in the library — not enough to work "
            "from. Research the subject before attempting it, and leave behind a "
            "plan plus the capabilities it needs."),
    }


# ---------------------------------------------------------------------------
# 2. The figure of merit — declared before anything is compared
# ---------------------------------------------------------------------------

def define_fom(topic: str, name: str, direction: str, target: float,
               measure: str) -> Dict[str, Any]:
    """Declare the figure of merit for *topic*: the one number that decides.

    Declared **before** approaches are compared, and that ordering is the point.
    A figure of merit chosen after the results are in is not a criterion, it is a
    justification — whichever number happened to favour the approach already
    preferred becomes "the metric we optimised". Fixing it first makes the later
    comparison a calculation instead of a defence.

    ``measure`` is required and must say *how* the number is obtained, because a
    metric nobody can reproduce cannot be checked by a corrector, and an
    unfalsifiable figure of merit is worse than none: it confers the appearance
    of rigour on an unmeasured choice.

    ``target`` is the threshold the chosen approach must actually reach. Without
    it a comparison only ranks candidates, and the best of several inadequate
    options passes as success.
    """
    if direction not in ("max", "min"):
        return {"status": "error",
                "error": "direction must be 'max' (higher is better) or 'min'"}
    if not str(name).strip():
        return {"status": "error", "error": "the figure of merit needs a name"}
    if not str(measure).strip():
        return {"status": "error",
                "error": ("measure is required: state exactly how this number is "
                          "obtained (command, dataset, counter). A figure of merit "
                          "that cannot be re-measured cannot be verified, and an "
                          "unverifiable criterion is decoration.")}
    try:
        target_value = float(target)
    except (TypeError, ValueError):
        return {"status": "error", "error": f"target must be a number, got {target!r}"}

    record = load(topic)

    # Renaming the figure of merit after measurements exist silently unscores
    # every one of them.
    #
    # `rank_approaches` reads each approach's metric BY NAME, so an approach
    # measured under the old name reads as unscored under the new one — it drops
    # below approaches with worse numbers and below unmeasured ones. Measured on
    # pylint-7080: the refinement carrying the correct fix scored 1.0 under
    # `recursive_discovery_ignore_accuracy`, a later stage redeclared the metric
    # as `files_correctly_filtered`, and the refinement sorted BELOW a 0.5 — so
    # the attempt implemented something else and failed the same way, three runs
    # in a row. Fixing the metric in advance is the whole point of declaring it,
    # and nothing enforced it.
    existing = record.get("fom") or {}
    wanted = str(name).strip()
    if existing.get("name") and existing["name"] != wanted:
        measured = [a.get("name") for a in record.get("approaches", [])
                    if (a.get("metrics") or {}).get(existing["name"]) is not None]
        if measured:
            return {
                "status": "error",
                "error": (f"the figure of merit for this topic is already "
                          f"{existing['name']!r} and {len(measured)} approach(es) "
                          f"have been measured against it. Renaming it now would "
                          f"unscore every one of them — they would rank below "
                          f"approaches nobody has measured at all. Keep measuring "
                          f"{existing['name']!r}; if it is genuinely the wrong "
                          f"criterion, say so in the report rather than "
                          f"substituting a new one after the results are in."),
                "fom": existing,
                "measured_against_it": measured[:6],
            }

    record["fom"] = {"name": wanted, "direction": direction,
                     "target": target_value, "measure": str(measure).strip(),
                     "at": time.time()}
    path = _save(record)
    return {"status": "ok", "topic": topic, "fom": record["fom"], "file": str(path),
            "next": (f"record candidate approaches, each measuring {name!r} the way "
                     "described, then call research_choose")}


#: Markers that a source lies outside the checkout being worked on.
_EXTERNAL_MARKERS = ("http://", "https://", "github.com", "gitlab", "issue",
                     "pull request", " pr ", "#", "changelog", "docs", "manual",
                     "man page", "--help", "commit", "release notes", "rfc",
                     "stack overflow", "mailing list")


def _looks_external(source: str) -> bool:
    """Whether a recorded source points outside the local working copy.

    Deliberately generous — a URL, an issue number, a changelog, a man page or a
    tool's own ``--help`` all count. The check exists to catch the case where
    *nothing* was consulted beyond the code in front of the agent, not to police
    citation style.
    """
    text = source.lower()
    return any(marker in text for marker in _EXTERNAL_MARKERS)


def rank(approaches: List[Dict[str, Any]], metric: str,
         prefer: str) -> List[Dict[str, Any]]:
    """The single ordering used to choose AND to check the choice.

    Measured before predicted, then by the metric. Defined once because
    :func:`choose` and :func:`verify_plan` previously each had their own idea of
    "best": choose ranked measurement first, the corrector ranked on the raw
    value, and so the corrector failed a choice that was correct by the rule the
    chooser had applied. Two definitions of the same decision is one too many.
    """
    return sorted(approaches,
                  key=lambda a: (bool(a.get("measured")),
                                 a["metrics"][metric] if prefer == "max"
                                 else -a["metrics"][metric]),
                  reverse=True)


def _meets(value: float, fom: Dict[str, Any]) -> bool:
    """Whether *value* satisfies the declared figure of merit's target."""
    if fom["direction"] == "max":
        return value >= fom["target"]
    return value <= fom["target"]


def record_achieved(topic: str, value: float, note: str = "") -> Dict[str, Any]:
    """Record the figure of merit actually achieved once the plan was executed.

    Separate from the approach's predicted number on purpose. The predicted value
    is what a candidate promised during research; this is what the work delivered.
    Keeping both is what lets :func:`verify_plan` catch research that looked
    convincing and did not hold — the single most useful thing a corrector can
    say about a plan.
    """
    record = load(topic)
    if not record.get("fom"):
        return {"status": "error",
                "error": "no figure of merit declared for this topic; call "
                         "research_define_fom first"}
    try:
        achieved = float(value)
    except (TypeError, ValueError):
        return {"status": "error", "error": f"value must be a number, got {value!r}"}

    record["achieved"] = {"value": achieved, "note": str(note), "at": time.time()}
    _save(record)
    fom = record["fom"]
    return {"status": "ok", "topic": topic, "achieved": achieved,
            "target": fom["target"], "meets_target": _meets(achieved, fom)}


# ---------------------------------------------------------------------------
# 3. Candidate approaches, compared on numbers
# ---------------------------------------------------------------------------

def add_approach(topic: str, name: str, summary: str,
                 hypothesis: str = "",
                 metrics: Optional[Dict[str, float]] = None,
                 source: str = "", tools: Optional[List[str]] = None,
                 measurement: str = "", aspect: str = "") -> Dict[str, Any]:
    """Record one candidate way of doing *topic*, with whatever was measured.

    ``metrics`` are numbers the researcher actually obtained — a benchmark
    figure, a count of steps, a measured runtime, tests passed. Recording the
    source alongside makes a claim checkable later; an approach with no source
    and no metrics is an opinion, and :func:`choose` will not select on it.
    """
    if not str(name).strip():
        return {"status": "error", "error": "approach name is required"}
    if not str(hypothesis).strip():
        return {"status": "error",
                "error": ("hypothesis is required: state what you believe is "
                          "true and what would show it false, e.g. 'the pattern "
                          "is matched against an un-normalised path, so any "
                          "relative form fails; a dotted path that matches after "
                          "normpath would confirm it'. An approach without a "
                          "hypothesis cannot be refuted, only abandoned — and "
                          "the next session re-derives it because nothing says "
                          "what was already ruled out.")}

    record = load(topic)

    # An approach a real task tried and failed must not come back.
    #
    # Prompt-level discouragement was not enough: sympy-24066 re-proposed the
    # same idea across four attempts, each round rediscovering that it did not
    # work, because nothing on the write path could tell "not tried yet" from
    # "tried and lost". This can. The refusal names what happened, so the caller
    # has something to reason from rather than an unexplained rejection.
    for existing in record.get("approaches", []):
        if str(existing.get("name", "")) != str(name):
            continue
        if existing.get("status") in ("failed", "falsified"):
            return {
                "status": "error",
                "error": (f"{name!r} was already tried and did not work "
                          f"(status {existing['status']}). Two ways forward, and "
                          f"the test output decides which:\n"
                          f"- if the failure shows the idea was RIGHT but the "
                          f"change was incomplete — the code ran, in the right "
                          f"place, and missed a case — call "
                          f"research_refine_approach(topic=..., "
                          f"key={existing.get('key', '')!r}, diagnosis=..., "
                          f"change=...). That keeps the ground the attempt won;\n"
                          f"- if it shows the idea was WRONG, propose something "
                          f"genuinely different. Re-proposing this one unchanged "
                          f"costs another full attempt to rediscover the same "
                          f"result."),
                "evidence": str(existing.get("outcome_evidence", ""))[:300],
                "refine_with": existing.get("key", ""),
                "already_dead": dead_approaches(topic),
            }
        break

    declared = (record.get("fom") or {}).get("name", "")
    supplied = dict(metrics or {})
    # Self-assessed scores are not evidence. Left unchecked, approaches arrive
    # carrying metrics like {"hypothesis_clarity": 0.8, "reproducible": 1.0} —
    # numbers the agent invented about its own idea, in fields nothing compares.
    # The figure of merit is computed from held-out trials; anything else is
    # dropped rather than stored where it can later be mistaken for measurement.
    rejected_metrics = [k for k in supplied if declared and k != declared]
    for key in rejected_metrics:
        supplied.pop(key, None)

    entry = {
        "name": name,
        "summary": summary,
        # What this approach claims, in falsifiable terms. The instances test
        # the hypothesis; the status records the verdict.
        "hypothesis": str(hypothesis).strip(),
        # Which research aspect turned it up, when exploration was split.
        "aspect": str(aspect).strip(),
        "metrics": {k: float(v) for k, v in supplied.items()},
        "source": source,
        "tools": list(tools or []),
        # How the numbers were obtained. Empty means they were predicted.
        #
        # This distinction is the difference between a comparison and a
        # rationalisation. Measured live: two runs of the same task, same model,
        # same prompts. One asserted 1.0 for normalising in _is_ignored_file and
        # produced the upstream fix; the other asserted 1.0 for filtering in
        # _discover_files and produced a patch that fixes nothing. Both were the
        # argmax of their own record, and the corrector called both "pass",
        # because an argmax over predictions returns whatever the agent already
        # believed.
        "measurement": str(measurement).strip(),
        "measured": bool(str(measurement).strip()),
        # Every approach starts POTENTIAL and stays there until the task
        # actually passes with it. Nothing is "the chosen approach" on the
        # strength of an argument — `working` is a status the tests confer, and
        # `falsified` is one they take away.
        "status": "potential",
        "at": time.time(),
    }

    # A stable key, allocated once and never recycled.
    #
    # Names are long, and everything that refers to an approach — the ranked
    # plan, the checkpoint, the record of what a task tried — had to spell one
    # out in full. A key is four characters, so the plan can list every
    # candidate for the price of one name, and the solve step can say which one
    # it is on without carrying its description around.
    #
    # Never recycled, for the same reason skill labels are not: a reused key
    # silently redirects every existing reference to different content, and here
    # that would mean a failed approach's key pointing at a live one.
    previous = next((a for a in record["approaches"] if a["name"] == name), None)
    used = {str(a.get("key") or "") for a in record["approaches"]}
    if previous and previous.get("key"):
        entry["key"] = previous["key"]
    else:
        index = 1
        while f"A{index}" in used:
            index += 1
        entry["key"] = f"A{index}"

    record["approaches"] = [a for a in record["approaches"] if a["name"] != name]
    record["approaches"].append(entry)
    path = _save(record)
    result = {"status": "ok", "topic": topic, "approach": name,
              "key": entry["key"],
              "approaches": len(record["approaches"]), "file": str(path)}
    if rejected_metrics:
        result["ignored_metrics"] = rejected_metrics
        result["note"] = (
            f"dropped {', '.join(rejected_metrics)}: the only metric that counts "
            f"is {declared!r}, and it is computed from trials on held-out "
            "instances rather than supplied here. Self-scored numbers about your "
            "own approach are not evidence.")
    return result


def choose(topic: str, metric: str = "", prefer: str = "",
           min_margin: float = 0.0) -> Dict[str, Any]:
    """Pick the best approach for *topic* by *metric*. Arithmetic, not opinion.

    This is the corrector for the research step, and it is deliberately willing
    to fail. It returns ``inconclusive`` when fewer than two approaches carry the
    metric, or when the winner's margin over the runner-up is within
    ``min_margin``. A comparison that cannot distinguish two options should say
    so; picking anyway is how "we evaluated the alternatives" gets attached to a
    choice that was never actually made.
    """
    record = load(topic)
    fom = record.get("fom")
    # Default to the declared figure of merit. Choosing on some other metric is
    # possible but must be explicit: silently ranking on whatever was passed in
    # is how a decision drifts away from the criterion it was supposed to serve.
    if not metric:
        if not fom:
            return {"status": "error",
                    "error": ("no figure of merit declared for this topic. Call "
                              "research_define_fom first — approaches cannot be "
                              "compared before the criterion exists, and a metric "
                              "picked afterwards is a justification, not a test.")}
        metric, prefer = fom["name"], fom["direction"]
    prefer = prefer or (fom["direction"] if fom else "max")
    if prefer not in ("max", "min"):
        return {"status": "error", "error": "prefer must be 'max' or 'min'"}
    scored = [a for a in record["approaches"] if metric in a.get("metrics", {})]
    if len(scored) < 2:
        return {
            "status": "inconclusive",
            "topic": topic,
            "reason": (
                f"{len(scored)} approach(es) carry metric {metric!r}; at least 2 "
                "are needed to choose between them. Measure the alternatives on "
                "the same metric, or record why only one is viable."),
            "approaches": [a["name"] for a in record["approaches"]],
        }

    measured = [a for a in scored if a.get("measured")]
    if not measured:
        return {
            "status": "inconclusive",
            "topic": topic,
            "reason": (
                f"none of the {len(scored)} approaches measured {metric!r} — every "
                "value is a prediction. Apply the leading candidates and run the "
                "measurement the figure of merit describes, then record the result "
                "with research_add_approach(..., measurement='how you got it'). "
                "An argmax over predictions returns the approach you already "
                "preferred, which is not a comparison."),
            "approaches": [a["name"] for a in scored],
        }

    ordered = rank(scored, metric, prefer)
    best, runner_up = ordered[0], ordered[1]
    margin = abs(best["metrics"][metric] - runner_up["metrics"][metric])

    # A measured number beating a predicted one is not a tie, however close the
    # values are: the measurement IS the difference between them. Treating it as
    # a tie would send the researcher off to separate two candidates when one of
    # them is only an opinion.
    decided_by_measurement = bool(best.get("measured")) and not runner_up.get("measured")

    if margin <= min_margin and not decided_by_measurement:
        return {
            "status": "inconclusive",
            "topic": topic,
            "reason": (
                f"{best['name']!r} and {runner_up['name']!r} differ by {margin:g} "
                f"on {metric!r}, within the {min_margin:g} margin. Either measure "
                "something that separates them or record that they are equivalent "
                "and pick on a stated secondary criterion."),
            "tied": [best["name"], runner_up["name"]],
        }

    record["chosen"] = {"name": best["name"], "metric": metric, "prefer": prefer,
                        "value": best["metrics"][metric], "margin": margin,
                        "measured": bool(best.get("measured")),
                        "at": time.time()}
    _save(record)
    return {"status": "ok", "topic": topic, "chosen": best["name"],
            "metric": metric, "value": best["metrics"][metric],
            "margin": margin, "runner_up": runner_up["name"],
            "ranking": [a["name"] for a in ordered]}


# ---------------------------------------------------------------------------
# 4. The plan, split into what is mechanical and what is not
# ---------------------------------------------------------------------------

def write_plan(topic: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Record the plan for *topic*: ordered steps, each tagged by kind.

    Each step needs ``title``, ``kind`` (``deterministic``/``judgement``) and
    ``detail``. The tag decides what the step becomes:

    * ``deterministic`` -> a capability. Same inputs, same outputs, every run.
    * ``judgement``     -> a skill block. Guidance for a decision that genuinely
      needs one.

    Rejecting an untagged step rather than defaulting: defaulting to
    ``judgement`` quietly turns mechanical work into prose, which is the failure
    this whole split exists to prevent, and defaulting to ``deterministic``
    promises repeatability the step cannot deliver.
    """
    cleaned = _clean_steps(steps)
    if isinstance(cleaned, dict):
        return cleaned

    record = load(topic)
    record["plan"] = cleaned
    path = _save(record)
    deterministic = [s for s in cleaned if s["kind"] == "deterministic"]
    return {
        "status": "ok",
        "topic": topic,
        "steps": len(cleaned),
        "deterministic": [s["title"] for s in deterministic],
        "judgement": [s["title"] for s in cleaned if s["kind"] == "judgement"],
        "file": str(path),
        "next": (
            f"{len(deterministic)} step(s) are deterministic and must become "
            "capabilities via capability_new before this plan is followed by "
            "hand; the judgement steps become skill blocks via skill_write."
            if deterministic else
            "no deterministic steps — if that is right, every step genuinely "
            "needs a decision. Re-read them: 'run the tests and read the failure' "
            "is mechanical."),
    }


def candidates(topic: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Approaches worth implementing and measuring, best-first.

    The alternative to ranking predictions and betting the attempt on the
    winner. Each of these is meant to be *built* — in its own checkout, by its
    own agent — and judged by the tests, so the figure of merit stops being a
    number the researcher asserted and becomes one the benchmark obtained.

    Already-falsified locations are dropped: an approach whose recorded
    measurement missed the target is not a candidate, it is a finished
    experiment. Approaches the ledger created from previous attempts are dropped
    too — they describe what was already tried, not a fresh idea to try.
    """
    record = load(resolve_topic(topic))
    fom = record.get("fom") or {}
    out: List[Dict[str, Any]] = []
    for entry in record.get("approaches", []):
        if entry.get("source") == "benchmark attempt":
            continue          # the ledger's own record of what was tried
        if entry.get("status") == "falsified":
            continue          # measured and it did not work: settled
        out.append({
            "name": entry.get("name", ""),
            "summary": entry.get("summary", ""),
            "source": entry.get("source", ""),
            "predicted": (entry.get("metrics") or {}).get(fom.get("name", "")),
            "status": entry.get("status", "potential"),
        })
    # A known-working approach first — if one exists there is nothing to explore.
    # Otherwise the open questions, best-predicted first.
    out.sort(key=lambda c: (c["status"] != "working", -(c["predicted"] or 0)))
    return out[:max(1, limit)]


def confirmed_approach(topic: str) -> Optional[Dict[str, Any]]:
    """The approach that passed the unseen instances, if one has."""
    record = load(resolve_topic(topic))
    for entry in record.get("approaches", []):
        if entry.get("status") == "confirmed":
            return entry
    return None


def record_measurement(topic: str, name: str, value: float,
                       how: str) -> Dict[str, Any]:
    """Record what an implemented approach actually scored, and set its status.

    An approach becomes ``working`` only when the measured figure of merit meets
    its target — that is, when the task really passed with it. Anything else
    measured becomes ``falsified``: a finished experiment that no later session
    should spend an agent on again.

    This is the only place a status changes. Nothing is promoted by argument.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    fom = record.get("fom") or {}
    if not fom:
        return {"status": "error", "error": "no figure of merit declared"}
    for entry in record["approaches"]:
        if entry.get("name") != name:
            continue
        entry.setdefault("metrics", {})[fom["name"]] = float(value)
        entry["measurement"] = how
        entry["measured"] = True
        entry["status"] = "confirmed" if _meets(float(value), fom) else "falsified"
        if entry["status"] == "confirmed":
            record["chosen"] = {"name": name, "metric": fom["name"],
                                "prefer": fom["direction"], "value": float(value),
                                "margin": 0.0, "measured": True,
                                "confirmed_by": how, "at": time.time()}
        _save(record)
        return {"status": "ok", "approach": name, "value": float(value),
                "approach_status": entry["status"]}
    return {"status": "error", "error": f"no approach named {name!r}"}


# ---------------------------------------------------------------------------
# The instance corpus, its diversity, and the split over it
# ---------------------------------------------------------------------------

def declare_corpus(topic: str, dimensions: Dict[str, List[str]],
                   target: int = DEFAULT_CORPUS_TARGET,
                   rationale: str = "") -> Dict[str, Any]:
    """Declare what varies across this task's instances, and how many are wanted.

    ``dimensions`` names the axes along which cases can differ and the values
    each can take — for a path-matching bug that might be
    ``{"path_form": ["relative", "absolute", "dotted"], "target": ["file",
    "directory", "package"], "separator": ["posix", "windows"]}``.

    Diversity cannot be defined once for all tasks, which is why it is declared
    per topic rather than hard-coded. What it buys is specific: instances
    generated without stated axes cluster around whatever the author was already
    thinking about, so the held-out set ends up testing the same idea the
    approach was built from and confirms it for free.

    ``target`` below :data:`DEFAULT_CORPUS_TARGET` requires a ``rationale``. Some
    tasks genuinely admit only a handful of distinct cases; saying so is fine,
    quietly shrinking the corpus until it fits what was already built is not.
    """
    if not dimensions:
        return {"status": "error",
                "error": ("declare at least one dimension — the axes along which "
                          "instances differ. Without them, 'diverse' is an "
                          "assertion nobody can check.")}
    try:
        target = int(target)
    except (TypeError, ValueError):
        return {"status": "error", "error": f"target must be a number, got {target!r}"}
    if target < DEFAULT_CORPUS_TARGET and not str(rationale).strip():
        return {"status": "error",
                "error": (f"target {target} is below the default "
                          f"{DEFAULT_CORPUS_TARGET}; state a rationale for why "
                          "this task cannot support more distinct cases")}

    topic = resolve_topic(topic)
    record = load(topic)
    record["corpus"] = {
        "target": target,
        "dimensions": {k: list(v) for k, v in dimensions.items()},
        "rationale": str(rationale)[:400],
        "at": time.time(),
    }
    _save(record)
    combos = 1
    for values in dimensions.values():
        combos *= max(1, len(values))
    return {"status": "ok", "topic": topic, "target": target,
            "dimensions": record["corpus"]["dimensions"],
            "distinct_combinations": combos,
            "next": (f"generate instances covering these axes — {combos} distinct "
                     "combinations exist. Writing a generator and registering it "
                     "with capability_new beats authoring them one at a time.")}


def add_instances(topic: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Add many instances at once. Phases are assigned later, by :func:`split`.

    Each entry needs ``name`` and ``behaviour``; ``dimensions`` places it on the
    declared axes, and ``command``/``expected`` make it re-runnable.

    Instances arrive without a phase deliberately. When the author chooses which
    case is held out, the held-out set drifts toward cases the approach already
    handles — not by dishonesty, just by the same intuition that produced the
    approach. Assigning phases by hash removes the choice.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    pool = record.setdefault("instances", [])
    by_name = {i["name"]: i for i in pool}

    added, rejected = 0, []
    for entry in instances or []:
        name = str(entry.get("name", "")).strip()
        behaviour = str(entry.get("behaviour", "")).strip()
        if not name or not behaviour:
            rejected.append(f"{name or '(unnamed)'}: name and behaviour are required")
            continue
        by_name[name] = {
            "name": name,
            "behaviour": behaviour,
            "command": str(entry.get("command", "")).strip(),
            "expected": str(entry.get("expected", "")).strip(),
            "dimensions": {str(k): str(v) for k, v in
                           (entry.get("dimensions") or {}).items()},
            "source": str(entry.get("source", "")).strip(),
            "at": time.time(),
        }
        added += 1

    pool[:] = list(by_name.values())
    # The split is invalidated: assignments must cover the new cases too.
    record.pop("split", None)
    _save(record)

    corpus = record.get("corpus") or {}
    target = corpus.get("target", DEFAULT_CORPUS_TARGET)
    return {"status": "ok", "topic": topic, "added": added,
            "total": len(pool), "target": target,
            "rejected": rejected[:5],
            "next": ("call research_split to assign phases"
                     if len(pool) >= target else
                     f"{target - len(pool)} more instance(s) before the corpus "
                     "meets its declared target")}


def coverage(topic: str) -> Dict[str, Any]:
    """How well the corpus covers the declared axes, and where it is thin.

    Reports per-value counts rather than a single diversity score: a score hides
    which axis is unrepresented, and an axis with one value is not a dimension,
    it is a constant that happens to be written down.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    corpus = record.get("corpus") or {}
    declared = corpus.get("dimensions") or {}
    pool = record.get("instances", [])

    seen: Dict[str, Dict[str, int]] = {}
    for axis, values in declared.items():
        counts = {value: 0 for value in values}
        for entry in pool:
            value = (entry.get("dimensions") or {}).get(axis)
            if value is not None:
                counts[value] = counts.get(value, 0) + 1
        seen[axis] = counts

    thin = {axis: [v for v, n in counts.items() if n == 0]
            for axis, counts in seen.items()}
    thin = {axis: values for axis, values in thin.items() if values}
    unplaced = [e["name"] for e in pool if not e.get("dimensions")]

    return {
        "status": "ok",
        "topic": topic,
        "instances": len(pool),
        "target": corpus.get("target", DEFAULT_CORPUS_TARGET),
        "meets_target": len(pool) >= corpus.get("target", DEFAULT_CORPUS_TARGET),
        "by_dimension": seen,
        "uncovered_values": thin,
        "instances_without_dimensions": unplaced[:10],
    }


def split(topic: str, seed: int = 0,
          ratios: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Assign every instance a phase, deterministically and stratified.

    Deterministic because a split that changes between calls makes "held out"
    meaningless — an instance that was test yesterday and train today has been
    seen. The assignment is a hash of the instance name and the seed, so the same
    corpus and seed always produce the same split, on any machine.

    Stratified by the declared dimensions so that each phase covers the axes
    rather than, say, putting every Windows-separator case in train. Strata are
    assigned round-robin through the phase quota, which spreads small strata
    across phases instead of dumping each one wholesale into whichever phase its
    hash picked.
    """
    import hashlib

    topic = resolve_topic(topic)
    record = load(topic)
    pool = record.get("instances", [])
    if not pool:
        return {"status": "error", "error": "no instances to split"}

    weights = dict(ratios or DEFAULT_SPLIT)
    total = sum(weights.values()) or 1.0
    weights = {phase: weights.get(phase, 0.0) / total for phase in PHASES}

    strata: Dict[str, List[Dict[str, Any]]] = {}
    for entry in pool:
        key = "|".join(f"{k}={v}" for k, v in
                       sorted((entry.get("dimensions") or {}).items())) or "(unplaced)"
        strata.setdefault(key, []).append(entry)

    assignment: Dict[str, str] = {}
    for key, members in sorted(strata.items()):
        ordered = sorted(members, key=lambda e: hashlib.sha256(
            f"{seed}:{e['name']}".encode()).hexdigest())
        for index, entry in enumerate(ordered):
            position = (index + 0.5) / len(ordered)
            running = 0.0
            for phase in PHASES:
                running += weights[phase]
                if position <= running or phase == PHASES[-1]:
                    assignment[entry["name"]] = phase
                    break

    # Every phase must receive at least one instance when the corpus can afford
    # it. Proportional assignment over small strata can empty a phase entirely,
    # and an empty test split silently disables the only phase that decides
    # anything: nothing can be confirmed and nothing falsified, so every approach
    # stays "potential" forever while appearing to be under evaluation.
    warnings: List[str] = []
    if len(pool) >= len(PHASES):
        for phase in PHASES:
            if any(p == phase for p in assignment.values()):
                continue
            donor_phase = max(
                PHASES, key=lambda ph: sum(1 for p in assignment.values() if p == ph))
            movable = sorted(name for name, ph in assignment.items()
                             if ph == donor_phase)
            if len(movable) > 1:
                assignment[movable[-1]] = phase
                warnings.append(f"moved 1 instance from {donor_phase} to {phase} "
                                "so no phase is empty")
    elif len(pool) < len(PHASES):
        warnings.append(f"only {len(pool)} instance(s): too few to fill three "
                        "phases, so the split cannot support a real held-out set")

    if len(pool) < MIN_CORPUS_INSTANCES:
        held_out = sum(1 for p in assignment.values() if p == "test")
        warnings.append(
            f"{len(pool)} instance(s) is below the {MIN_CORPUS_INSTANCES} this "
            f"corpus needs: the held-out set is {held_out} case(s), and a score "
            f"over {held_out} can be reached by accident. Add instances along "
            f"the axes you declared — including negative cases, which is where "
            f"a change that ignores everything gets caught.")

    record["split"] = {"seed": seed, "ratios": weights,
                       "assignment": assignment, "at": time.time()}
    _save(record)

    counts = {phase: sum(1 for p in assignment.values() if p == phase)
              for phase in PHASES}
    # Named explicitly, because the 80:20 that matters is tuning against unseen,
    # not the three-way split it happens to be implemented as.
    counts["tuning"] = sum(counts[phase] for phase in TUNING_PHASES)
    counts["held_out"] = counts["test"]
    return {"status": "ok", "topic": topic, "seed": seed, "counts": counts,
            "strata": len(strata), "warnings": warnings,
            "next": "run each approach against the train and validate splits; "
                    "touch test once, at the end"}


def phase_of(record: Dict[str, Any], instance: str) -> str:
    """The phase an instance was assigned, or "" when no split has been made."""
    return ((record.get("split") or {}).get("assignment") or {}).get(instance, "")


# ---------------------------------------------------------------------------
# Instances, trials, and promotion
# ---------------------------------------------------------------------------

def add_instance(topic: str, name: str, behaviour: str, command: str = "",
                 expected: str = "", dimensions: Optional[Dict[str, str]] = None,
                 source: str = "") -> Dict[str, Any]:
    """Record a task instance the researcher authored, in one of :data:`PHASES`.

    An instance is a concrete case that exhibits the behaviour under study —
    a reproducer script, an input/expected pair, a command with a known result.
    They are cheap to build and cheap to run, which is the point: an approach can
    be checked against a dozen of them for a fraction of what it costs to build
    the approach for real and put it through the full evaluation.

    ``behaviour`` says what the instance demonstrates. ``command`` and
    ``expected`` make it re-runnable by anyone, which is what stops "I checked
    it" from being the whole record.
    """
    return add_instances(topic, [{"name": name, "behaviour": behaviour,
                                  "command": command, "expected": expected,
                                  "dimensions": dimensions or {},
                                  "source": source}])


def _phase_counts(record: Dict[str, Any]) -> Dict[str, int]:
    """How many instances landed in each phase, per the current split."""
    counts = {phase: 0 for phase in PHASES}
    for phase in ((record.get("split") or {}).get("assignment") or {}).values():
        counts[phase] = counts.get(phase, 0) + 1
    return counts


def _instance_advice(counts: Dict[str, int]) -> str:
    missing = [phase for phase in PHASES if not counts.get(phase)]
    if missing:
        return (f"no instances yet for: {', '.join(missing)}. An approach cannot "
                "be validated without cases it was not built against.")
    return "all three phases have instances; build an approach and run trials"


def record_trial(topic: str, approach: str, instance: str, passed: bool,
                 detail: str = "") -> Dict[str, Any]:
    """Record how one approach fared on one instance.

    Trials are the evidence :func:`evaluate_approach` aggregates. Recording a
    failure is as valuable as recording a pass — an approach with no failed
    trials anywhere has usually not been tried hard enough to be believed.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    known = {i["name"]: i for i in record.get("instances", [])}
    if instance not in known:
        return {"status": "error",
                "error": f"no instance named {instance!r}; add it to the corpus "
                         "first with research_add_instances"}
    phase = phase_of(record, instance)
    if not phase:
        return {"status": "error",
                "error": ("this corpus has not been split yet — call "
                          "research_split so phases are assigned by hash rather "
                          "than by choice")}

    trials = record.setdefault("trials", [])
    trials[:] = [t for t in trials
                 if not (t["approach"] == approach and t["instance"] == instance)]
    trials.append({"approach": approach, "instance": instance,
                   "phase": phase, "passed": bool(passed),
                   "detail": str(detail)[:400], "at": time.time()})
    _save(record)
    return {"status": "ok", "approach": approach, "instance": instance,
            "phase": phase, "passed": bool(passed)}


def evaluate_approach(topic: str, approach: str) -> Dict[str, Any]:
    """Aggregate an approach's trials and set its status. Deterministic.

    The promotion rule, and nothing else decides:

    ``confirmed``   passes every ``validate`` and every ``test`` instance, with
                    at least one of each. The only status that licenses writing
                    the approach up as a skill and using it for the task.
    ``validated``   tuned until it passes validation; the unseen test instances
                    have not been run yet, so correctness is still a claim.
    ``falsified``   fails an instance in ``test``. Only this phase falsifies.
    ``potential``   still being worked on, or not enough evidence.

    Failing ``train`` or ``validate`` does **not** falsify. Train is where
    approaches are discovered and validate is where they are tuned — an approach
    that fails there is unfinished, not refuted. Treating tuning failures as
    refutations would push the real work somewhere unrecorded and throw away
    candidates that only needed another iteration.

    Conversely, passing validate proves very little on its own: an approach tuned
    until it passes its own tuning set has demonstrated only that it can be
    tuned. That is why ``confirmed`` requires the unseen set.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    fom_name = (record.get("fom") or {}).get("name", "")
    trials = [t for t in record.get("trials", []) if t["approach"] == approach]
    by_phase = {phase: [t for t in trials if t["phase"] == phase] for phase in PHASES}

    summary = {phase: {"passed": sum(1 for t in rows if t["passed"]),
                       "total": len(rows)}
               for phase, rows in by_phase.items()}

    def clean(phase: str) -> bool:
        rows = by_phase[phase]
        return bool(rows) and all(t["passed"] for t in rows)

    # Only the unseen set refutes. Validate is a tuning surface, so failing it
    # means "not finished", and an approach discarded for that reason is a
    # candidate thrown away for doing exactly what the phase is for.
    failed_unseen = any(not t["passed"] for t in by_phase["test"])

    if failed_unseen:
        status = "falsified"
    elif clean("validate") and clean("test"):
        status = "confirmed"
    elif clean("validate"):
        status = "validated"
    else:
        status = "potential"

    # The figure of merit, COMPUTED from the trials rather than asserted.
    #
    # The instances supply the evidence; the figure of merit remains what
    # approaches are judged on. Deriving it here is what keeps both true at once
    # — the number is the one the topic declared, and its value is a measurement
    # nobody had to be trusted for.
    #
    # Scored on the held-out material only. Train performance is not quality: it
    # is the set the approach was derived from, and including it rewards fitting
    # the cases you invented.
    held_out = by_phase["validate"] + by_phase["test"]
    score = (sum(1 for t in held_out if t["passed"]) / len(held_out)
             if held_out else None)

    for entry in record.get("approaches", []):
        if entry.get("name") == approach:
            entry["status"] = status
            entry["trials"] = summary
            if score is not None and fom_name:
                entry.setdefault("metrics", {})[fom_name] = round(score, 4)
                entry["measurement"] = (
                    f"pass rate over {len(held_out)} held-out instance(s): "
                    f"validate {summary['validate']['passed']}/"
                    f"{summary['validate']['total']}, test "
                    f"{summary['test']['passed']}/{summary['test']['total']}")
                entry["measured"] = True
            if status == "confirmed":
                record["chosen"] = {
                    "name": approach, "metric": (record.get("fom") or {}).get("name"),
                    "value": None, "margin": 0.0, "measured": True,
                    "confirmed_by": "train/validate/test trials", "at": time.time()}
            break
    else:
        return {"status": "error", "error": f"no approach named {approach!r}"}

    _save(record)
    return {"status": "ok", "approach": approach, "approach_status": status,
            "phases": summary,
            fom_name or "score": score,
            "reason": _promotion_reason(status, summary)}


def _promotion_reason(status: str, summary: Dict[str, Dict[str, int]]) -> str:
    if status == "confirmed":
        return ("passes every held-out instance; write it up as a skill and use "
                "it for the task")
    if status == "validated":
        return ("tuned until it passes validation, which on its own only shows "
                "it can be tuned. Run the unseen test instances before writing "
                "it up")
    if status == "falsified":
        return ("fails an unseen test instance — it was fitted to the cases it "
                "was tuned against. Keep the record; it stops a later session "
                "re-proposing it")
    missing = [p for p in PHASES if not summary[p]["total"]]
    return (f"not enough evidence: no trials on {', '.join(missing)}"
            if missing else "not enough evidence yet")


def backups(topic: str) -> List[Dict[str, Any]]:
    """Approaches still worth trying, best-first. What a retry starts from.

    The reason research does not begin again from nothing when an attempt fails:
    the alternatives it already found, with their trial results, are still on
    record. A retry picks up the next one instead of re-deriving the same set of
    ideas at full cost.
    """
    record = load(resolve_topic(topic))
    out = []
    for entry in record.get("approaches", []):
        if entry.get("source") == "benchmark attempt":
            continue
        if entry.get("status") in ("falsified", "confirmed"):
            continue
        out.append({
            "name": entry.get("name", ""),
            "summary": entry.get("summary", ""),
            "source": entry.get("source", ""),
            "status": entry.get("status", "potential"),
            "trials": entry.get("trials", {}),
        })
    order = {"validated": 0, "potential": 1}
    out.sort(key=lambda c: order.get(c["status"], 2))
    return out


def set_aspects(topic: str, aspects: List[Dict[str, str]]) -> Dict[str, Any]:
    """Record the research plan: the aspects to investigate, before investigating.

    Naming the aspects up front is what makes parallel exploration possible and
    what stops it becoming duplication — four investigators with no assigned
    angle produce four versions of the same first idea. Each aspect is a distinct
    place the answer could be: the project's own history, the code path that
    consumes the value, the code path that produces it, the configuration that
    governs it.

    Recorded before the work so that reconciliation has something to reconcile
    *against*, and so an aspect nobody covered is visible as a gap rather than an
    absence nobody noticed.
    """
    cleaned = []
    for index, aspect in enumerate(aspects or [], 1):
        name = str(aspect.get("name", "")).strip()
        question = str(aspect.get("question", "")).strip()
        if not name or not question:
            return {"status": "error",
                    "error": f"aspect {index} needs a name and a question"}
        cleaned.append({"name": name, "question": question,
                        "where": str(aspect.get("where", "")).strip()})
    if not cleaned:
        return {"status": "error", "error": "a research plan needs at least one aspect"}

    topic = resolve_topic(topic)
    record = load(topic)
    record["aspects"] = cleaned
    _save(record)
    return {"status": "ok", "topic": topic, "aspects": [a["name"] for a in cleaned],
            "next": "investigate the aspects independently, then reconcile the "
                    "approaches they produced"}


def rank_approaches(topic: str) -> Dict[str, Any]:
    """Order the approaches by how they scored on the metric. Deterministic.

    Stage seven of the flow, and it needs no agent: the trials are on record and
    the ordering is arithmetic. Asking a model to rank results it can already see
    invites it to re-argue the ones it liked, which is the failure the metric was
    introduced to prevent.

    Unscored approaches sort last, not first: an approach nobody evaluated is not
    a strong candidate, it is an unknown one.
    """
    record = load(resolve_topic(topic))
    fom = record.get("fom") or {}
    name = fom.get("name", "")
    prefer_max = fom.get("direction", "max") == "max"

    rows = []
    for entry in record.get("approaches", []):
        if entry.get("source") == "benchmark attempt":
            continue
        # A superseded approach is the earlier draft of the one that replaced
        # it, and listing both offers the solve step its own predecessor.
        # Observed: `append-trailing-sep-only` ranked FIRST at 1.0 while the
        # revision that added the missing normalisation sat second and
        # unmeasured, so the attempt implemented the version already known to
        # be incomplete — the refinement was made and then ranked out of reach.
        if entry.get("superseded_by"):
            continue
        value = (entry.get("metrics") or {}).get(name)
        rows.append({
            "key": entry.get("key", ""),
            "name": entry.get("name", ""),
            "score": value,
            # Where it sits in the order when it has no score of its own.
            "sort_score": None,
            "refines": entry.get("refines", ""),
            # Whether a measured patch exists, never the patch itself.
            "change_patch": entry.get("change_patch", ""),
            # The steps this approach runs. What makes it something the next
            # attempt can fall back TO rather than read about.
            "pipeline": entry.get("pipeline") or [],
            # The steps this approach runs. What makes it a candidate the next
            # attempt can actually fall back TO rather than read about.
            "pipeline": entry.get("pipeline") or [],
            "status": entry.get("status", "potential"),
            "hypothesis": entry.get("hypothesis", ""),
            "summary": entry.get("summary", ""),
            "source": entry.get("source", ""),
            "trials": entry.get("trials", {}),
        })

    # A refinement takes its parent's PLACE in the order, not its score.
    #
    # It starts unmeasured by design, so on score alone it sorts below every
    # approach the corpus happened to number — including unrelated ones — and
    # the leading line of thinking silently drops to the bottom of the list the
    # moment it is improved. Ordering on the parent's number keeps the position
    # the lineage earned; `score` stays None, so nothing downstream can mistake
    # the parent's measurement for the revision's.
    # Built from EVERY entry, not from `rows`: the parent of a refinement has
    # just been filtered out for being superseded, and looking the lineage up in
    # the filtered list finds nothing at all.
    entries = {str(e.get("key") or ""): e for e in record.get("approaches", [])
               if e.get("key")}
    for row in rows:
        parent = entries.get(str(row.get("refines") or ""))
        seen = {row["key"]}
        while parent is not None and row["sort_score"] is None:
            row["sort_score"] = (parent.get("metrics") or {}).get(name)
            parent_key = str(parent.get("key") or "")
            if parent_key in seen:
                break
            seen.add(parent_key)
            parent = entries.get(str(parent.get("refines") or ""))

    def key(row: Dict[str, Any]) -> Any:
        value = row["score"] if row["score"] is not None else row["sort_score"]
        scored = value is not None
        # Ties go to the refinement, and it is not a coin-toss.
        #
        # A refinement is the only candidate informed by what the REAL task did:
        # it exists because an attempt was made, judged, and diagnosed, and it
        # carries the reproduction of the failure it fixes. Its rivals scored on
        # a corpus the research session wrote for itself and have never been
        # tried on anything. Measured on pylint-7080: the refinement carrying
        # the missing normalisation tied at 1.0 with two untried approaches,
        # lost the tie to insertion order, and the attempt implemented one of
        # them instead — failing exactly as the attempt before it had.
        return (not scored,
                -value if (scored and prefer_max) else (value or 0.0),
                not row.get("refines"))

    rows.sort(key=key)
    return {"status": "ok", "topic": topic, "metric": name,
            "direction": fom.get("direction", "max"),
            "target": fom.get("target"),
            "ranking": rows,
            "best": rows[0]["name"] if rows else None,
            "unscored": [r["name"] for r in rows if r["score"] is None]}


def select(topic: str) -> Dict[str, Any]:
    """The approach to act on. Always returns one when any exist.

    "No approach selected" is not a usable answer to "what should I do now". The
    attempt has to implement *something*, and refusing to name a candidate does
    not prevent a choice — it just moves the choice somewhere unrecorded, where
    it cannot be reviewed or falsified later.

    So selection always yields a best-available candidate, with its status and
    the confidence that status carries:

    ``confirmed``  passed the held-out instances — act on it
    ``validated``  passed tuning, unseen set not yet run — act, and finish the run
    ``potential``  best available on the evidence so far — act, and say so

    Only an empty record returns nothing, and that is a different failure: it
    means research produced no candidates at all.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    fom = record.get("fom") or {}
    live = [a for a in record.get("approaches", [])
            if a.get("source") != "benchmark attempt"
            and a.get("status") != "falsified"]
    if not live:
        falsified = [a for a in record.get("approaches", [])
                     if a.get("status") == "falsified"]
        covered = {a.get("aspect") for a in record.get("approaches", []) if a.get("aspect")}
        planned = [a["name"] for a in record.get("aspects", [])]
        unexplored = [name for name in planned if name not in covered]
        # Exhausting the candidates means the search was too narrow, not that the
        # task is impossible. Every one of these was a hypothesis that has now
        # been tested, which is a better starting point than the blank page the
        # first round began from — so this returns a direction, not a stop.
        return {
            "status": "exhausted" if falsified else "empty",
            "topic": topic,
            "reason": (f"all {len(falsified)} approach(es) falsified"
                       if falsified else "no approaches recorded yet"),
            "falsified": [a["name"] for a in falsified],
            "ruled_out_hypotheses": [a.get("hypothesis", "") for a in falsified if a.get("hypothesis")],
            "unexplored_aspects": unexplored,
            "next": (
                "Do NOT stop. Every falsified hypothesis narrows where the cause "
                "can be, so widen the search rather than repeating it: "
                + (f"aspects planned but never investigated: {', '.join(unexplored)}. "
                   if unexplored else
                   "add aspects nobody has looked at — the caller, the producer of "
                   "the value, the configuration that governs it, the project's "
                   "own history. ")
                + "Then record new approaches with hypotheses that the falsified "
                  "ones would not have predicted."),
        }

    rank_order = {"confirmed": 0, "validated": 1, "potential": 2}

    def score(entry: Dict[str, Any]) -> Any:
        value = (entry.get("metrics") or {}).get(fom.get("name", ""))
        # Higher is better unless the figure of merit says otherwise; unscored
        # approaches sort last within their status band.
        if value is None:
            ordered_value = float("-inf")
        else:
            ordered_value = value if fom.get("direction", "max") == "max" else -value
        return (rank_order.get(entry.get("status"), 3), -ordered_value)

    best = sorted(live, key=score)[0]
    status = best.get("status", "potential")
    confidence = {
        "confirmed": "passed the held-out instances",
        "validated": "passed tuning; the unseen set has not been run",
        "potential": "best available on the evidence so far, not yet confirmed",
    }.get(status, status)

    return {
        "status": "ok",
        "topic": topic,
        "selected": best["name"],
        "approach_status": status,
        "hypothesis": best.get("hypothesis", ""),
        "summary": best.get("summary", ""),
        "source": best.get("source", ""),
        "score": (best.get("metrics") or {}).get(fom.get("name", "")),
        "confidence": confidence,
        "alternatives": [a["name"] for a in sorted(live, key=score)[1:4]],
    }


def best_score(topic: str) -> Dict[str, Any]:
    """The best figure of merit any approach has reached on held-out instances.

    The number research is actually trying to move. Time and record size are
    proxies for progress; this is progress.
    """
    record = load(resolve_topic(topic))
    fom = record.get("fom") or {}
    name = fom.get("name", "")
    scored = [(a.get("metrics", {}).get(name), a)
              for a in record.get("approaches", [])
              if a.get("measured") and name in (a.get("metrics") or {})]
    if not scored:
        return {"status": "ok", "best": None, "meets_target": False,
                "approach": None, "measured_approaches": 0}

    pick = (max if fom.get("direction", "max") == "max" else min)
    value, entry = pick(scored, key=lambda row: row[0])
    return {"status": "ok", "best": value, "approach": entry.get("name"),
            "meets_target": _meets(float(value), fom),
            "measured_approaches": len(scored),
            "target": fom.get("target")}


def record_pass_score(topic: str) -> Dict[str, Any]:
    """Append the current best score to the history. One entry per research pass.

    Kept as a series rather than a single number because the useful question is
    not "how good is it" but "is it still getting better" — a pass that moves
    nothing is the signal to stop, and that is invisible without the previous
    value to compare against.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    current = best_score(topic)
    history = record.setdefault("score_history", [])
    history.append({"pass": len(history) + 1, "best": current.get("best"),
                    "approach": current.get("approach"),
                    "measured_approaches": current.get("measured_approaches", 0),
                    "at": time.time()})
    _save(record)
    return {"status": "ok", "history": history, "best": current.get("best")}


def improvement_stalled(topic: str, window: int = 2,
                        epsilon: float = 0.01) -> Dict[str, Any]:
    """Whether the last *window* passes moved the figure of merit at all.

    Metric-based, not size-based. A pass can add approaches, instances and trials
    — growing every count the record keeps — while the best held-out score sits
    exactly where it was, which is activity rather than progress. ``epsilon``
    exists because a score that creeps by a thousandth is also not progress.
    """
    record = load(resolve_topic(topic))
    history = record.get("score_history", [])
    if len(history) <= window:
        return {"stalled": False,
                "reason": f"only {len(history)} pass(es) recorded"}

    recent = [h.get("best") for h in history[-(window + 1):]]
    if any(value is None for value in recent):
        measured = [h for h in history[-(window + 1):]
                    if h.get("measured_approaches")]
        if not measured:
            return {"stalled": False,
                    "reason": "nothing has been measured yet, so there is no "
                              "score to stall"}
        recent = [value for value in recent if value is not None]

    gain = max(recent) - min(recent)
    return {"stalled": gain <= epsilon,
            "gain": round(gain, 4),
            "window": window,
            "reason": (f"best score moved {gain:.3f} across the last {window} "
                       f"pass(es), within the {epsilon} threshold"
                       if gain <= epsilon else
                       f"best score improved by {gain:.3f}")}


def _fit(lines: List[str], limit: int, note: str = "") -> str:
    """Join what fits, and say what did not. Blocks are rejected, not truncated.

    ``skills.write_block`` refuses an over-long body rather than cutting it —
    correctly, since a half-sentence stored as complete knowledge is worse than
    an error. But a *generated* body has no author to act on that error: the
    playbook's ranked list simply exceeded 1400 characters with three approaches
    on record, the write was refused, and the stage reported success anyway. The
    agent then spent its remaining budget searching the filesystem for a store
    that is only reachable through MCP tools.

    So generated bodies are fitted here, and what is dropped is named.
    """
    kept: List[str] = []
    used = 0
    reserve = len(note) + 40
    for line in lines:
        if used + len(line) + 1 > limit - reserve:
            remaining = len(lines) - len(kept)
            if note and remaining > 0:
                kept.append("")
                kept.append(note.format(n=remaining))
            break
        kept.append(line)
        used += len(line) + 1
    return "\n".join(kept).strip()


def _catalogue_description(record: Dict[str, Any], name: str) -> str:
    """The one line retrieval scores a skill on, built from the record itself.

    This was `f"What research established about {name}."` and that sentence is
    the reason harvesting bought nothing. Retrieval scores a skill's subject,
    description and Index rows; a description containing only the words already
    in the name adds no vocabulary, so a later task asking about "ignore-paths
    not respected during recursive file discovery" scored the harvested skill at
    zero and reported a gap — with the answer sitting in the store.

    The record already holds the right words, in the researcher's own phrasing:
    the aspect questions say what was investigated, the approach names say what
    was tried. Both are folded in verbatim, because the point is to match the
    *next* asker's vocabulary rather than to read well.
    """
    subject = name.replace("-", " ")
    parts: List[str] = []

    for aspect in (record.get("aspects") or [])[:3]:
        question = str(aspect.get("question", "")).strip().rstrip("?")
        if question:
            parts.append(question[0].lower() + question[1:])

    tried = [str(a.get("name", "")).replace("-", " ").strip()
             for a in (record.get("approaches") or [])]
    tried = [t for t in tried if t][:4]

    text = f"Research on {subject}."
    if parts:
        text += " Covers " + "; ".join(parts) + "."
    if tried:
        text += " Approaches tried: " + ", ".join(tried) + "."
    return text[:600]


def harvest(topic: str, skill: str = "") -> Dict[str, Any]:
    """Turn a research record into durable skill blocks. Deterministic.

    Without this, everything research learns dies with the topic. The record is
    per-task, so the next task on the same subsystem re-runs the same searches,
    re-reads the same upstream issue, re-derives the same approaches and
    re-discovers the same dead ends — at full price, every time.

    Harvesting is done by code rather than by asking the agent to write it up,
    for the same reason the ledger is: the material is already on disk in
    structured form, and a step that depends on an agent remembering to do it at
    the end of a long session is a step that will sometimes not happen.

    What each part of the record becomes:

    ``confirmed approach``   a **rule** — where the fix goes and why it holds
    ``falsified approach``   a **lesson** — what was tried and what refuted it
    ``sources``              a **reference** — the issue, commit or docs
    ``metric`` + ``corpus``  an **instruction** — how to evaluate work on this
                             subject next time, which is the expensive part to
                             re-derive

    The skill is named for the *subject*, not the task, so the next instance in
    the same area finds it. A skill called after one bug is never retrieved again.
    """
    from phronix import skills

    topic = resolve_topic(topic)
    record = load(topic)
    approaches = [a for a in record.get("approaches", [])
                  if a.get("source") != "benchmark attempt"]
    if not approaches and not record.get("fom"):
        return {"status": "empty", "topic": topic,
                "reason": "nothing on record worth keeping"}

    name = _slug(skill or _topic_skill(record, topic))
    description = _catalogue_description(record, name)
    written: List[Dict[str, Any]] = []

    def write(kind: str, title: str, body: str) -> None:
        if not body.strip():
            return
        result = skills.write_block(name, kind, title, body,
                                    description=description)
        written.append({"kind": kind, "title": title,
                        "status": (result or {}).get("status", "?")})

    fom = record.get("fom") or {}
    corpus = record.get("corpus") or {}
    if fom:
        axes = ", ".join(corpus.get("dimensions", {}).keys())
        write("instruction", f"How to evaluate a change to {name.replace('-', ' ')}",
              f"Figure of merit: **{fom.get('name')}** "
              f"({fom.get('direction')}, target {fom.get('target')}).\n\n"
              f"Measured by: {str(fom.get('measure', ''))[:400]}\n\n"
              + (f"Cases differ along: {axes}." if axes else ""))

    for entry in approaches:
        title = str(entry.get("name", ""))[:90]
        hypothesis = str(entry.get("hypothesis", ""))[:400]
        summary = str(entry.get("summary", ""))[:300]
        trials = entry.get("trials") or {}
        evidence = ", ".join(f"{phase} {counts.get('passed', 0)}/{counts.get('total', 0)}"
                             for phase, counts in trials.items()
                             if counts.get("total"))

        if entry.get("status") == "confirmed":
            write("rule", f"Fix this in {summary[:60] or title}",
                  f"{summary}\n\nWhy it holds: {hypothesis}\n\n"
                  f"Confirmed on held-out instances ({evidence or 'trials recorded'}).")
        elif entry.get("status") in ("potential", "validated"):
            # Recorded even though it has not settled. "This was tried" is the
            # cheapest thing to know and the most expensive to rediscover: a
            # later session that sees only confirmed and falsified approaches
            # has no way to tell an untried idea from one already investigated,
            # and will spend a full round finding out.
            write("reference", f"Tried: {title}",
                  f"{summary}\n\n**Hypothesis**: {hypothesis}\n\n"
                  f"**Status**: {entry.get('status')} "
                  f"({evidence or 'no trials recorded yet'}). "
                  "Investigated already — extend this rather than re-deriving it.")
        elif entry.get("status") == "falsified":
            skills.write_lesson(
                name,
                f"**Tried**: {title}\n\n**Hypothesis**: {hypothesis}\n\n"
                f"**Refuted by**: {evidence or 'held-out trials'}. "
                "Do not re-propose this without new evidence.",
                kind="pitfall", title=f"{title} does not work",
                description=f"What research established about "
                            f"{name.replace('-', ' ')}.")
            written.append({"kind": "pitfall", "title": title, "status": "ok"})

    sources = sorted({str(a.get("source", "")).strip() for a in approaches
                      if _looks_external(str(a.get("source", "")))})
    if sources:
        write("reference", f"Sources consulted for {name.replace('-', ' ')}",
              "\n".join(f"- {source[:200]}" for source in sources[:8]))

    record["harvested"] = {"skill": name, "blocks": len(written),
                           "at": time.time()}
    _save(record)
    return {"status": "ok", "topic": topic, "skill": name,
            "written": written,
            "next": f"future tasks on this subject will find {name!r} through "
                    "research_assess and can skip the search"}


def _merge_records(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Fold one topic record into another. Union, never replace.

    Two sessions can research the same subject — that is the normal case once a
    task list repeats a subsystem — and whichever synced last would otherwise
    erase the other's approaches. Approaches are unioned by name, with the
    measured version winning a tie, because a measurement is the thing that was
    expensive to obtain.
    """
    merged = dict(base)
    for key in ("fom", "corpus", "plan", "chosen", "split", "achieved"):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]

    by_name: Dict[str, Dict[str, Any]] = {}
    for entry in list(base.get("approaches") or []) + list(incoming.get("approaches") or []):
        name = str(entry.get("name", ""))
        if not name:
            continue
        current = by_name.get(name)
        if current is None:
            by_name[name] = entry
            continue
        # Prefer the one that was measured; then the one further along.
        rank = {"working": 4, "confirmed": 3, "validated": 2,
                "potential": 1, "falsified": 0}
        better = (bool(entry.get("measured")), rank.get(entry.get("status"), 1))
        worse = (bool(current.get("measured")), rank.get(current.get("status"), 1))
        if better > worse:
            by_name[name] = entry
    merged["approaches"] = list(by_name.values())

    for key in ("aspects", "instances"):
        seen, rows = set(), []
        for entry in list(base.get(key) or []) + list(incoming.get(key) or []):
            name = str(entry.get("name", ""))
            if name and name not in seen:
                seen.add(name)
                rows.append(entry)
        if rows:
            merged[key] = rows

    merged["attempts_log"] = (list(base.get("attempts_log") or [])
                              + list(incoming.get("attempts_log") or []))
    return merged


def sync_session(session: str = "") -> Dict[str, Any]:
    """Fold a finished session's research into the common, checked-in folder.

    Called once a session is over. Until then its records stay in its own folder
    so the run cannot read its way out of the isolation it was given.

    Merges rather than overwrites: two sessions researching one subject is the
    normal case as soon as a task list revisits a subsystem, and a plain copy
    would let whichever finished last erase the other's approaches.
    """
    home = _research_home()
    name = _slug(session or os.environ.get(SESSION_ENV, "").strip())
    if not name:
        return {"status": "empty", "reason": "no session to sync"}

    folder = home / SESSIONS_DIR / name
    if not folder.is_dir():
        return {"status": "empty", "session": name, "reason": "no such session"}

    synced: List[str] = []
    for path in sorted(folder.glob("*.json")):
        try:
            incoming = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        target = home / path.name
        record = incoming
        if target.is_file():
            try:
                record = _merge_records(
                    json.loads(target.read_text(encoding="utf-8")), incoming)
            except (OSError, json.JSONDecodeError):
                record = incoming
        try:
            target.write_text(json.dumps(record, indent=2), encoding="utf-8")
            synced.append(path.stem)
        except OSError:
            continue

    return {"status": "ok", "session": name, "synced": synced,
            "into": str(home)}


def prior_work(question: str, limit: int = 4) -> Dict[str, Any]:
    """Everything already on record that bears on this question. Deterministic.

    The first thing a research pass should do, and until now there was no way to
    do it. Research carries across runs, so by the third task on a subsystem the
    store holds several records, a playbook skill and a set of approaches that
    were tried — and the pass would still open by surveying the subject from
    nothing, because the only lookups available were keyed on the current
    topic, which is by construction new.

    Three sources, because each misses what the others catch:

    * **skills** — the retrieval index, which is good at matching a symptom
      described in the asker's words against a subject described in somebody
      else's;
    * **research records** — scored on their own vocabulary, and the only place
      the *approaches* live: what was tried, what was refuted, what worked;
    * **settled aspects** — ground already covered well enough to re-check
      rather than re-investigate.

    The graph is deliberately not called here. Freshening it shells out to
    graphify and can take minutes, which is the wrong thing to do inside a
    lookup that exists to save time; the agent calls ``graph_query`` itself when
    it wants to go wider.

    Returns a digest small enough to paste into a prompt.
    """
    from phronix import skills

    terms = set(skills._terms(question))
    found_skills: List[Dict[str, Any]] = []
    try:
        hits = skills.search(question, max_results=limit) or {}
        for hit in hits.get("results") or []:
            found_skills.append({"skill": hit.get("skill"),
                                 "why": str(hit.get("description", ""))[:200]})
    except Exception:
        pass

    scored: List[Any] = []
    for topic in list_topics():
        try:
            record = load(topic)
        except Exception:
            continue

        # The record's own vocabulary: what it is about, what it asked, what it
        # tried. Matching on the topic key alone would never fire — the keys are
        # per-task and every task's key is new.
        vocabulary = [str(record.get("topic", ""))]
        vocabulary += [str(a.get("name", "")) + " " + str(a.get("question", ""))
                       for a in record.get("aspects") or []]
        vocabulary += [str(a.get("name", "")) + " " + str(a.get("hypothesis", ""))
                       for a in record.get("approaches") or []]
        record_terms = set(skills._terms(" ".join(vocabulary)))
        overlap = terms & record_terms
        if not overlap:
            continue

        approaches = []
        for entry in record.get("approaches") or []:
            approaches.append({
                "name": entry.get("name", ""),
                "status": entry.get("status", "potential"),
                "measured": bool(entry.get("measured")),
                "hypothesis": str(entry.get("hypothesis", ""))[:200],
                "source": str(entry.get("source", ""))[:120],
            })

        settled = []
        for aspect in record.get("aspects") or []:
            name = str(aspect.get("name", ""))
            if name and settled_aspect(name):
                settled.append(name)

        scored.append((len(overlap), {
            "topic": topic,
            "matched_on": sorted(overlap)[:8],
            "approaches": approaches[:8],
            "settled_aspects": settled,
            "fom": (record.get("fom") or {}).get("name", ""),
        }))

    scored.sort(key=lambda row: -row[0])
    topics = [row[1] for row in scored[:limit]]

    tried = sorted({a["name"] for t in topics for a in t["approaches"] if a["name"]})
    working = sorted({a["name"] for t in topics for a in t["approaches"]
                      if a["status"] == "working"})
    refuted = sorted({a["name"] for t in topics for a in t["approaches"]
                      if a["status"] == "falsified"})
    settled_all = sorted({name for t in topics for name in t["settled_aspects"]})

    return {
        "status": "ok" if (topics or found_skills) else "nothing on record",
        "question": question,
        "skills": found_skills,
        "topics": topics,
        "already_tried": tried,
        "known_working": working,
        "known_refuted": refuted,
        "settled_aspects": settled_all,
        "advice": (
            "Do not re-derive any of the above. Approaches under "
            "`already_tried` have been proposed before — propose something "
            "different unless you have new evidence. Aspects under "
            "`settled_aspects` only need re-checking against this version."
            if (tried or settled_all) else
            "Nothing on record bears on this question; research it properly."),
    }


def settled_aspect(name: str) -> Optional[Dict[str, Any]]:
    """Has earlier research already established this aspect, anywhere on record?

    Looks across every topic, not just the current one. That is the point: the
    second task on a subsystem gets a *different* topic key, so a same-topic
    lookup would never fire and every task would re-investigate ground the last
    one covered — at 300 seconds an aspect, three aspects at a time.

    "Settled" is deliberately strict. An aspect counts only if the record it
    appears in produced at least one **measured** approach citing it. An aspect
    that was investigated and yielded nothing measurable is not settled; it is
    unfinished, and skipping it would bury the fact.

    Returns the aspect with the findings that cite it, or None. None is the
    normal answer and means "investigate it properly".
    """
    target = _slug(name)
    for topic in list_topics():
        try:
            record = load(topic)
        except Exception:
            continue

        aspects = {_slug(str(a.get("name", ""))): a
                   for a in record.get("aspects") or []}
        if target not in aspects:
            continue

        # Approaches that came out of this aspect AND carry a measurement.
        supporting = [a for a in record.get("approaches") or []
                      if _slug(str(a.get("aspect", ""))) == target
                      and a.get("measured")]
        if not supporting:
            continue

        findings = []
        for entry in supporting[:4]:
            parts = [f"- **{entry.get('name', '?')}** "
                     f"({entry.get('status', 'potential')})"]
            for label, key in (("hypothesis", "hypothesis"),
                               ("where", "summary"), ("evidence", "source")):
                value = str(entry.get(key, "")).strip()
                if value:
                    parts.append(f"  {label}: {value[:240]}")
            findings.append("\n".join(parts))

        return {"aspect": aspects[target], "from_topic": topic,
                "findings": "\n".join(findings),
                "approaches": [a.get("name") for a in supporting]}
    return None


def checkpoint(topic: str) -> Dict[str, Any]:
    """Where research on this topic stands, written down. Deterministic, always.

    A retry used to re-enter the flow and rebuild its picture of the subject
    from the record — tens of kilobytes of accumulated working detail — or, when
    a stage had been truncated, from whatever fragment survived. Either way the
    next pass paid again for ground the last one had covered.

    So after every stage the state is dumped: what is established, what is still
    open, what has been ruled out, and *references* to where the detail lives if
    a later pass genuinely needs it. The next attempt reads this and continues,
    rather than starting over.

    This is code, not an agent, and it has no time limit. That is the point —
    the dumping must never be the thing that gets cut off, because a stage
    truncated while writing up loses everything the stage before it paid for.
    """
    from phronix import skills

    topic = resolve_topic(topic)
    record = load(topic)
    approaches = record.get("approaches") or []
    if not approaches and not record.get("fom"):
        return {"status": "empty", "topic": topic}

    name = _slug(_topic_skill(record, topic))
    fom = record.get("fom") or {}

    settled, open_questions, dead = [], [], []
    for entry in approaches:
        label = str(entry.get("name", "?"))
        status = str(entry.get("status", "potential"))
        score = (entry.get("metrics") or {}).get(fom.get("name", ""))
        measured = f" {fom.get('name')}={score}" if score is not None else ""
        row = f"- {label} ({status}{measured})"
        if status in ("falsified", "failed"):
            # "failed" means a real task was attempted with it and lost — the
            # strongest evidence available, and the reason it must never come
            # back as a candidate.
            note = str(entry.get("outcome_evidence", "")).strip()
            dead.append(row + (f" — {note[:90]}" if note else ""))
        elif entry.get("measured") or status in ("working", "confirmed"):
            settled.append(row)
        else:
            open_questions.append(row)

    covered = {_slug(str(a.get("aspect", ""))) for a in approaches if a.get("aspect")}
    for aspect in record.get("aspects") or []:
        label = str(aspect.get("name", ""))
        if label and _slug(label) not in covered:
            open_questions.append(f"- aspect not yet answered: {label}")

    lines = [f"State of research on this subject as of the last stage that ran.",
             ""]
    if fom:
        lines += [f"Measured by **{fom.get('name')}** "
                  f"({fom.get('direction')}, target {fom.get('target')}).", ""]
    for heading, rows in (("Established", settled),
                          ("Still open", open_questions),
                          ("Ruled out", dead)):
        if rows:
            lines.append(f"**{heading}**")
            lines += rows[:6]
            lines.append("")

    # References, not content. A later pass that needs the detail can go and get
    # it; one that does not should not pay to have it pasted here.
    references = []
    for entry in approaches[:6]:
        source = str(entry.get("source", "")).strip()
        if source:
            references.append(f"- {entry.get('name', '?')}: {source[:110]}")
    if references:
        lines.append("**Where the detail is**")
        lines += references
        lines.append(f"- full record: research topic `{topic}` "
                     f"(via research_status, only if this summary is not enough)")

    body = _fit(lines, skills.BLOCK_LIMITS["reference"],
                "...and {n} more line(s); see the full record.")
    # replace=True: this block states current state, so a stale copy is worse
    # than none — a retry would resume from a picture several stages old.
    result = skills.write_block(
        name, "reference", "Where research on this subject stands", body,
        description=_catalogue_description(record, name), replace=True)

    record["checkpoint"] = {"at": time.time(), "skill": name,
                            "established": len(settled),
                            "open": len(open_questions), "ruled_out": len(dead)}
    _save(record)
    return {"status": "ok", "topic": topic, "skill": name,
            "established": len(settled), "open": len(open_questions),
            "block": (result or {}).get("status", "?")}


def playbook(topic: str, skill: str = "") -> Dict[str, Any]:
    """The execution plan, written as the skill that solves this class of task.

    The last stage of research used to produce a plan: a document, scoped to one
    task, read once by the agent that followed it and then discarded with the
    run. Everything expensive about research — which approaches exist, which one
    measured best, which were tried and did not hold — was re-derived by the next
    task on the same subsystem.

    So the plan is a skill instead. Same content, but in the store, under the
    subject rather than the task, where retrieval will find it the next time
    somebody asks a question in this area.

    Every approach is written as **potential**, including the one that ranked
    first. Ranking well on a corpus the researcher built is evidence, not proof:
    the corpus was authored by the same session that proposed the approaches, so
    a high score can mean the approach is right or that the cases were shaped to
    suit it. Only a task actually passing promotes an approach — see
    :func:`mark_working` — and until then the skill offers the ranking as an
    order to try things in, which is what it honestly is.

    The skill is the *whole* of the collected research, not the ranking alone.
    :func:`harvest` supplies what the earlier stages established — the figure of
    merit and how to measure it, the sources consulted, the approaches already
    tried, the rules that held and the ones that were refuted — and this stage
    adds the ordering and what each aspect went looking for. One subject, one
    skill, everything the research produced, retrievable by the next task.

    Deterministic, for the same reason :func:`harvest` is: the ranking is already
    on disk, and a write-up that depends on an agent remembering to do it at the
    end of a long session is one that will sometimes not happen.
    """
    from phronix import skills

    topic = resolve_topic(topic)
    record = load(topic)
    ranked = rank_approaches(topic)
    rows = ranked.get("ranking") or []
    if not rows:
        return {"status": "empty", "topic": topic,
                "reason": "no approaches on record to write up"}

    name = _slug(skill or _topic_skill(record, topic))

    # Everything the earlier stages established, under the same subject.
    harvested = harvest(topic, skill=name)
    subject = name.replace("-", " ")
    metric = ranked.get("metric") or "the figure of merit"

    # The ordering, compactly. Each approach's hypothesis, evidence and where
    # the change goes is already a "Tried:" reference block written by
    # :func:`harvest`, so repeating it here would both duplicate the store and
    # blow the block limit — which is exactly what it did.
    lines = [
        f"Try these in order, ONE at a time. Ranked by measured **{metric}** "
        f"({ranked.get('direction', 'max')}, target {ranked.get('target')}).",
        "",
        "Take the first, get its detail with `research_approach(key=...)`, and "
        "implement only that. Move to the next one only if it fails. Reading "
        "them all up front costs context on every task including the ones the "
        "first approach solves, which is most of them.",
        "",
        "An approach marked **patch on file** carries `change_patch`: the exact "
        "diff that was applied and measured. `git apply` it and go straight to "
        "verifying — do not open it, and do not rebuild it by hand. That patch "
        "is the point of having researched at all.",
        "",
        "All are *potential*: they ranked on a corpus this research authored, "
        "which is a reason to try them in this order, not evidence any is "
        "correct. One becomes *working* when a task passes with it.",
        "",
    ]
    # Dead candidates never appear in a list headed "try these in order".
    #
    # They were still being numbered first, because ranking sorts on the metric
    # and a failed approach keeps whatever it scored. An agent told to work down
    # the list in order would open by re-implementing the thing that already
    # lost — the precise loop this is all meant to break.
    live = [r for r in rows if r.get("status") not in ("failed", "falsified")]
    buried = [r for r in rows if r.get("status") in ("failed", "falsified")]

    for position, row in enumerate(live, 1):
        score = row.get("score")
        measured = f"{score:.3f}" if isinstance(score, (int, float)) else "unmeasured"
        summary = str(row.get("summary", "")).strip()
        # The key leads. Whoever follows this plan works one approach at a time
        # and asks for the detail of that one by key; listing the full
        # description of all of them here would defeat the point.
        # A candidate that carries a measured patch says so HERE, in one word.
        #
        # It is the difference between an attempt that applies a change and one
        # that reconstructs it, and the reader decides that before asking for
        # any detail. The path itself stays out of the list: the attempt gets it
        # from `research_approach(key=...)` for the one candidate it is on, so a
        # plan listing five approaches does not carry five file paths nobody
        # will use.
        lines.append(f"{position}. `{row.get('key') or '?'}` "
                     f"**{row.get('name', '?')}** — {metric} {measured}, "
                     f"{row.get('status', 'potential')}"
                     + (" — **patch on file**" if row.get("change_patch") else "")
                     + (f" — {summary[:90]}" if summary else ""))

    if not live:
        lines.append("Every recorded approach has been tried and has failed. "
                     "That means the search was too narrow, not that the task "
                     "is impossible: look at a different layer, a different "
                     "mechanism, or how the project fixed this upstream.")

    if buried:
        lines.append("")
        lines.append("**Already tried against the real task and failed — do not "
                     "start here, and do not re-propose under a new name:**")
        for row in buried[:6]:
            lines.append(f"- `{row.get('key') or '?'}` {row.get('name', '?')}")

    ruled = record.get("ruled_out") or []
    if ruled:
        lines.append("")
        lines.append("Locations already changed without success: "
                     + ", ".join(str(x)[:40] for x in ruled[:6]) + ".")

    description = _catalogue_description(record, name)
    body = _fit(lines, skills.BLOCK_LIMITS["instruction"],
                "...and {n} lower-ranked approach(es); see `research_rank`.")
    result = skills.write_block(
        name, "instruction", f"How to solve {subject}", body,
        description=description, replace=True)

    # The plan, as the steps that DO the work — tools first, prose last.
    #
    # This is what the skill is for. A ranked list of approaches tells an agent
    # what to believe; a sequence of steps tells it what to run. Each step was
    # tagged when the plan was written: `deterministic` steps have a capability
    # built for them and are called by name, and only the steps that genuinely
    # need judgement arrive as instructions.
    #
    # The distinction is the whole economy of a researched attempt. A capability
    # runs the same way every time for the price of a tool call; an instruction
    # has to be read, interpreted and acted on, and it is read again on every
    # task that loads this skill. Measured: an attempt following prose reached
    # the right edit in six steps and spent forty-five more around it, at ~54k
    # tokens of working context per step.
    # Every live approach, in evaluated order, as the pipeline it runs.
    #
    # The solution file is not one method with alternatives described in prose:
    # it is the pipelines themselves, best first. An attempt that exhausts the
    # first approach needs the second one's STEPS, not a sentence about it —
    # otherwise the fallback path is exactly the unresearched attempt that this
    # whole apparatus exists to avoid.
    #
    # Compact by construction: the leading pipeline is rendered in full below,
    # and the alternates as one line per step. A skill carrying four pipelines
    # in full would exceed the block limit and be rejected, which is how a
    # fallback silently stops existing.
    alternates = [r for r in live[1:] if r.get("pipeline")]
    if alternates:
        fallback = ["If the leading approach fails, these were also measured. "
                    "Ranked by the same metric.", ""]
        for row in alternates[:3]:
            score = row.get("score")
            shown = f"{score:.3f}" if isinstance(score, (int, float)) else "unmeasured"
            fallback.append(f"**`{row.get('key')}` {row.get('name')}** — "
                            f"{metric} {shown}")
            for step in sorted(row.get("pipeline") or [],
                               key=lambda s: s.get("order", 0)):
                tool = str(step.get("capability", "")).strip()
                fallback.append(f"  {step.get('order', '?')}. "
                                + (f"`{tool}(...)`" if tool
                                   else f"{str(step.get('title', '?'))[:60]} "
                                        f"(judgement)"))
            fallback.append("")
        skills.write_block(
            name, "instruction", f"Fallback approaches for {subject}",
            _fit(fallback, skills.BLOCK_LIMITS["instruction"],
                 "...and {n} more line(s); see `research_rank`."),
            description=f"the next pipelines to try for {subject}, in order",
            replace=True)

    # Every live approach, in evaluated order, as the pipeline it runs.
    #
    # The solution file is not one method with alternatives described in prose:
    # it is the pipelines themselves, best first. An attempt that exhausts the
    # leading approach needs the next one's STEPS, not a sentence about it —
    # otherwise the fallback path is the unresearched attempt this whole
    # apparatus exists to avoid.
    #
    # Compact by construction: the leading pipeline is rendered in full below,
    # the alternates as one line per step. A skill carrying four pipelines in
    # full would exceed the block limit and be rejected, which is how a fallback
    # silently stops existing.
    alternates = [r for r in live[1:] if r.get("pipeline")]
    if alternates:
        fallback = ["If the leading approach fails, these were also measured, "
                    "ranked by the same metric.", ""]
        for row in alternates[:3]:
            score = row.get("score")
            shown = f"{score:.3f}" if isinstance(score, (int, float)) else "unmeasured"
            fallback.append(f"**`{row.get('key')}` {row.get('name')}** — "
                            f"{metric} {shown}")
            for step in sorted(row.get("pipeline") or [],
                               key=lambda item: item.get("order", 0)):
                tool = str(step.get("capability", "")).strip()
                fallback.append(f"  {step.get('order', '?')}. "
                                + (f"`{tool}(...)`" if tool
                                   else f"{str(step.get('title', '?'))[:60]} "
                                        "(judgement)"))
            fallback.append("")
        skills.write_block(
            name, "instruction", f"Fallback approaches for {subject}",
            _fit(fallback, skills.BLOCK_LIMITS["instruction"],
                 "...and {n} more line(s); see `research_rank`."),
            description=f"the next pipelines to try for {subject}, in order",
            replace=True)

    plan = record.get("plan") or []
    if plan:
        steps = [f"The steps that solve {subject}, in order. Run them.", ""]
        for step in sorted(plan, key=lambda s: s.get("order", 0)):
            title = str(step.get("title", "?")).strip()
            detail = str(step.get("detail", "")).strip()
            capability = str(step.get("capability", "")).strip()
            if capability:
                steps.append(f"{step.get('order', '?')}. `{capability}(...)` — "
                             f"{title}")
            else:
                # Named as a judgement call rather than left to look like a
                # tool nobody built: a step that reads as missing infrastructure
                # invites the agent to go looking for it.
                steps.append(f"{step.get('order', '?')}. **{title}** "
                             f"(judgement — no tool for this)")
                if detail:
                    steps.append(f"   {detail[:200]}")
        unbuilt = [s for s in plan
                   if s.get("kind") == "deterministic" and not s.get("capability")]
        if unbuilt:
            steps += ["", f"{len(unbuilt)} deterministic step(s) have no "
                          f"capability yet: " +
                      ", ".join(str(s.get("title", "?"))[:40] for s in unbuilt[:3])
                      + ". Build them with `capability_new` rather than doing "
                        "that work by hand again."]
        skills.write_block(
            name, "instruction", f"Steps to solve {subject}",
            _fit(steps, skills.BLOCK_LIMITS["instruction"],
                 "...and {n} further step(s); see `research_status`."),
            description=f"the ordered steps, tool by tool, for {subject}",
            replace=True)

    # What each aspect went looking for, and where. Kept because a later task
    # that needs to go further should know which ground was already covered —
    # and because an aspect that found nothing is a result worth not repeating.
    aspects = record.get("aspects") or []
    if aspects:
        investigated = ["Ground already covered by research on this subject.", ""]
        for aspect in aspects[:8]:
            question = str(aspect.get("question", "")).strip()
            where = str(aspect.get("where", "")).strip()
            if not question:
                continue
            investigated.append(f"- **{aspect.get('name', '?')}** — {question[:200]}")
            if where:
                investigated.append(f"  Looked in: {where[:160]}")
        skills.write_block(
            name, "reference", f"What has been investigated about {subject}",
            _fit(investigated, skills.BLOCK_LIMITS["reference"],
                 "...and {n} more line(s) of ground covered."),
            description=description, replace=True)

    written = (result or {}).get("status", "?")
    if written == "error":
        # Reporting `ok` alongside `block: error` is what sent an agent hunting
        # the filesystem for a store it can only reach through MCP tools, until
        # its budget ran out.
        return {"status": "error", "topic": topic, "skill": name,
                "error": (result or {}).get("error", "the skill block was refused"),
                "hint": "the generated block exceeded its limit — this is a bug "
                        "in research.playbook, not something to work around"}

    record.setdefault("harvested", {})["playbook"] = name
    _save(record)
    return {"status": "ok", "topic": topic, "skill": name,
            "ordered": [r.get("name") for r in rows],
            "harvested": (harvested or {}).get("written", []),
            "block": (result or {}).get("status", "?")}


def attempted_approach(topic: str) -> str:
    """The approach the next attempt will actually follow: the top live candidate.

    Recorded before the attempt runs so its outcome can be attributed to it
    afterwards. Without this the harness knows a task failed but not *what*
    failed, so the approach that lost stays a live candidate and gets proposed
    again — which is exactly what happened on sympy-24066, four times.
    """
    ranking = rank_approaches(topic).get("ranking") or []
    for row in ranking:
        if row.get("status") not in ("falsified", "failed"):
            return str(row.get("name") or "")
    return ""


def mark_attempt_outcome(topic: str, approach: str = "", worked: bool = False,
                         evidence: str = "") -> Dict[str, Any]:
    """Record what happened when a real task was solved with this approach.

    Both outcomes, which is the point. Only the success case existed, so an
    approach that had been tried and had failed was indistinguishable from one
    nobody had tried — it kept its status, kept its rank, and the next round
    proposed it again. sympy-24066 spent four attempts and 587k research tokens
    rediscovering one wrong idea.

    A failure here is stronger evidence than any corpus score. The corpus was
    written by the same session that proposed the approach; the task was not.
    So ``worked=False`` sets **failed**, which :func:`add_approach` then refuses
    to let anything re-propose.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    approach = approach or attempted_approach(topic)
    if not approach:
        return {"status": "empty", "topic": topic, "reason": "no approach named"}

    for entry in record.get("approaches", []):
        if approach not in (entry.get("name"), entry.get("key")):
            continue
        entry["status"] = "working" if worked else "failed"
        entry["decided_at"] = time.time()
        if evidence:
            entry["outcome_evidence"] = str(evidence)[:400]
        _save(record)
        checkpoint(topic)
        return {"status": "ok", "topic": topic, "approach": approach,
                "new_status": entry["status"]}

    return {"status": "unknown", "topic": topic, "approach": approach,
            "known": [e.get("name") for e in record.get("approaches", [])]}


#: How many times one line of thinking may be refined before it is abandoned.
#:
#: Refinement has to be bounded or it becomes the same failure it fixes. An
#: agent that can always say "nearly right, one more tweak" will spend every
#: retry on the first idea it had. Two revisions is enough for "right place,
#: missed a case"; a third means the diagnosis itself is wrong.
MAX_REFINEMENTS = 2


def refine_approach(topic: str, key: str, diagnosis: str, change: str,
                    hypothesis: str = "") -> Dict[str, Any]:
    """Carry a failed approach forward as a revision, instead of discarding it.

    Blanket refusal was too blunt. pylint-7080 failed with the ignore check in
    exactly the right function, on exactly the right line — and no
    normalisation, so ``./ignored_subdirectory/failing.py`` never matched an
    anchored pattern. The idea was right and one call short. Banning it outright
    sent the next attempt looking somewhere else, away from an answer it was a
    line from having.

    The two failures are different and the test output tells them apart:

    * the change never ran, or ran and the behaviour was untouched -> the idea
      is wrong, and :func:`add_approach` should keep refusing it;
    * the change ran, in the right place, and missed a case -> the idea is
      right, and what it needs is the missing case, not a replacement.

    So this is deliberately expensive to call: a *diagnosis* naming what the
    evidence showed, and a *change* naming what will be different. Without both
    it is a rename, which is the thing the refusal exists to stop.
    """
    topic = resolve_topic(topic)
    record = load(topic)

    parent = None
    for entry in record.get("approaches", []):
        if key in (entry.get("key"), entry.get("name")):
            parent = entry
            break
    if parent is None:
        return {"status": "unknown", "topic": topic, "key": key,
                "known": [f"{e.get('key')}:{e.get('name')}"
                          for e in record.get("approaches", [])]}

    if parent.get("status") not in ("failed", "falsified"):
        return {"status": "error",
                "error": (f"{parent['name']!r} is {parent.get('status')!r}, not a "
                          "failure — there is nothing to refine. Use it as it "
                          "stands.")}

    if len(str(diagnosis).strip()) < 40:
        return {"status": "error",
                "error": ("diagnosis must say what the failure output actually "
                          "showed, in enough detail to be checkable — which test, "
                          "what it printed, and why that means the idea was right "
                          "but incomplete. A short diagnosis is a guess, and "
                          "refining on a guess is how one wrong idea consumes "
                          "every remaining attempt.")}
    if len(str(change).strip()) < 25:
        return {"status": "error",
                "error": ("change must name what will be DIFFERENT this time, "
                          "concretely. 'Try again more carefully' is not a "
                          "change.")}

    depth = int(parent.get("refinement_depth") or 0) + 1
    if depth > MAX_REFINEMENTS:
        return {"status": "error",
                "error": (f"{parent['name']!r} has already been refined "
                          f"{MAX_REFINEMENTS} time(s) and still fails. At this "
                          f"point the diagnosis is what is wrong, not the "
                          f"implementation. Look somewhere genuinely different: "
                          f"another layer, another mechanism, or how the project "
                          f"itself fixed this upstream."),
                "already_dead": dead_approaches(topic)}

    name = f"{parent['name']}-r{depth}"
    used = {str(a.get("key") or "") for a in record["approaches"]}
    index = 1
    while f"A{index}" in used:
        index += 1

    entry = dict(parent)
    entry.update({
        "name": name,
        "key": f"A{index}",
        "status": "potential",
        # A revision starts unmeasured. Inheriting the parent's numbers would
        # let a score obtained by the version that FAILED rank the version that
        # replaced it, which is the one comparison this must not allow.
        "metrics": {},
        "measurement": "",
        "measured": False,
        "hypothesis": str(hypothesis).strip() or str(change).strip(),
        "summary": f"{parent.get('summary', '')}\n\nRevision {depth}: {change}",
        "refines": parent.get("key", ""),
        "refinement_depth": depth,
        "diagnosis": str(diagnosis).strip()[:600],
        "at": time.time(),
    })
    entry.pop("decided_at", None)
    entry.pop("outcome_evidence", None)

    parent["superseded_by"] = entry["key"]
    record["approaches"].append(entry)
    _save(record)
    checkpoint(topic)
    return {"status": "ok", "topic": topic, "approach": name, "key": entry["key"],
            "refines": parent.get("key", ""), "depth": depth,
            "remaining_refinements": MAX_REFINEMENTS - depth}


def final_revision(topic: str, key: str) -> Optional[Dict[str, Any]]:
    """The live end of a refinement lineage: what tuning actually left behind.

    Tuning may refine an approach more than once, and each revision is a new
    entry with a new key. Evaluating the key the stage STARTED from would score
    the version tuning already improved and discard the improvement, which is
    the one outcome that makes tuning worthless.

    Returns the last unsuperseded descendant of *key*, or the entry itself when
    nothing refined it. ``None`` when the key is unknown.
    """
    record = load(resolve_topic(topic))
    entries = {str(e.get("key") or ""): e for e in record.get("approaches", [])
               if e.get("key")}
    current = entries.get(str(key))
    seen = set()
    while current is not None:
        current_key = str(current.get("key") or "")
        successor = str(current.get("superseded_by") or "")
        if not successor or successor in seen:
            break
        seen.add(current_key)
        nxt = entries.get(successor)
        if nxt is None:
            break
        current = nxt
    return current


def mark_working(topic: str, approach: str = "") -> Dict[str, Any]:
    """A task passed using this approach. See :func:`mark_attempt_outcome`."""
    return mark_attempt_outcome(topic, approach, worked=True)


#: How much measured diff an approach may carry.
#:
#: A real fix for one of these tasks is tens of lines. Anything much larger is
#: not "the change", it is a working tree with debris in it — and pasting that
#: into the attempt's context is the opposite of the point.
CHANGE_LIMIT = 4000


def _clean_steps(steps: List[Dict[str, Any]]) -> Any:
    """Validate and normalise an ordered pipeline. Shared by plan and approach.

    One definition, because a pipeline recorded against an approach becomes the
    topic's plan verbatim when that approach wins — if the two disagreed about
    what a step is, the winner's pipeline would fail validation at the moment it
    was adopted, which is the worst possible time to find out.
    """
    if not steps:
        return {"status": "error", "error": "a pipeline needs at least one step"}

    cleaned: List[Dict[str, Any]] = []
    for index, step in enumerate(steps, 1):
        kind = str(step.get("kind", "")).strip().lower()
        title = str(step.get("title", "")).strip()
        if not title:
            return {"status": "error", "error": f"step {index} has no title"}
        if kind not in STEP_KINDS:
            return {"status": "error",
                    "error": (f"step {index} ({title!r}) has kind={kind!r}; must be "
                              f"one of {', '.join(STEP_KINDS)}. Deterministic steps "
                              "become MCP capabilities, judgement steps become skill "
                              "blocks — an untagged step becomes neither.")}
        cleaned.append({"order": index, "title": title, "kind": kind,
                        "detail": str(step.get("detail", "")).strip(),
                        "capability": str(step.get("capability", "")).strip(),
                        "skill": str(step.get("skill", "")).strip()})
    return cleaned


def record_pipeline(topic: str, key: str,
                    steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The ordered steps this approach actually runs. Its real content.

    An approach is a *way of solving the problem*, and the honest expression of
    a way is a sequence of steps — not a name and a paragraph of summary. The
    stage that tunes an approach has just run those steps to measure it, so it
    is the one place where the pipeline is known to be real rather than
    imagined, and recording it there costs nothing.

    Each step is tagged ``deterministic`` (it becomes a capability, called by
    name) or ``judgement`` (it stays prose, because it genuinely needs a model).

    The winner's pipeline is adopted as the topic's plan by
    :func:`adopt_pipeline`, and the playbook renders it into the skill. So the
    skill is not written *about* the best approach; it *is* the best approach,
    in the form that can be executed.
    """
    cleaned = _clean_steps(steps)
    if isinstance(cleaned, dict):
        return cleaned

    topic = resolve_topic(topic)
    record = load(topic)
    for entry in record.get("approaches", []):
        if key not in (entry.get("key"), entry.get("name")):
            continue
        entry["pipeline"] = cleaned
        entry["pipeline_at"] = time.time()
        _save(record)
        deterministic = [s["title"] for s in cleaned if s["kind"] == "deterministic"]
        return {"status": "ok", "topic": topic, "key": entry.get("key"),
                "approach": entry.get("name"), "steps": len(cleaned),
                "deterministic": deterministic,
                "next": ("build a capability for each deterministic step with "
                         "capability_new; every one built is work no future "
                         "attempt repeats")}
    return {"status": "unknown", "topic": topic, "key": key,
            "known": [f"{e.get('key')}:{e.get('name')}"
                      for e in record.get("approaches", [])]}


def adopt_pipeline(topic: str, key: str = "") -> Dict[str, Any]:
    """Make the chosen approach's pipeline the topic's plan.

    The execution plan is not a fresh piece of writing at the end of research —
    it is the winning approach's own steps, promoted. Writing it again by hand
    invites a fourth version of something already established three times, and
    the version the agent types at the end is the one nobody measured.

    Defaults to the top live candidate, which is the one the attempt will try.
    """
    topic = resolve_topic(topic)
    record = load(topic)

    chosen = None
    if key:
        chosen = next((e for e in record.get("approaches", [])
                       if key in (e.get("key"), e.get("name"))), None)
        if chosen is None:
            return {"status": "unknown", "topic": topic, "key": key}
    else:
        for row in rank_approaches(topic).get("ranking") or []:
            if row.get("status") in ("failed", "falsified"):
                continue
            chosen = next((e for e in record.get("approaches", [])
                           if e.get("key") == row.get("key")), None)
            if chosen and chosen.get("pipeline"):
                break
            chosen = None

    if chosen is None:
        return {"status": "empty", "topic": topic,
                "reason": ("no live approach carries a pipeline. The tuning "
                           "stage records one for the approach it measured — "
                           "if none did, write the plan directly with "
                           "research_write_plan.")}
    pipeline = chosen.get("pipeline") or []
    if not pipeline:
        return {"status": "empty", "topic": topic, "key": chosen.get("key"),
                "reason": f"{chosen.get('name')!r} has no pipeline recorded"}

    record["plan"] = [dict(step) for step in pipeline]
    record["plan_from"] = chosen.get("key")
    _save(record)
    unbuilt = [s["title"] for s in pipeline
               if s["kind"] == "deterministic" and not s.get("capability")]
    return {"status": "ok", "topic": topic, "key": chosen.get("key"),
            "approach": chosen.get("name"), "steps": len(pipeline),
            "needs_capability": unbuilt}


def record_change(topic: str, key: str, diff: str) -> Dict[str, Any]:
    """Save the measured change as a patch FILE and reference it from the approach.

    The tuning stage applies a candidate in its own worktree, runs the corpus
    against it, and then the worktree is discarded — so the one artefact known
    to work is thrown away and the attempt reconstructs it from a prose summary.
    Measured: an attempt reached the correct edit in six steps and spent
    forty-five more around it, at roughly 54k tokens of context per step.
    Re-deriving a change research already made is the largest avoidable cost in
    a researched attempt.

    Stored as a file rather than inline, and this is the point of it: the skill
    carries a PATH, the attempt runs ``git apply`` on it, and the diff never
    enters anyone's context at all. Inlining a 4 KB patch would put it in the
    skill, in the block that quotes the skill, and in every subsequent turn of
    the conversation — paying for the change repeatedly in order to avoid
    deriving it once.

    Captured by the harness with ``git diff`` rather than written out by an
    agent, so what the attempt applies is the change that was measured and not
    a description of it that may differ in exactly the detail that mattered.
    """
    diff = str(diff or "").strip()
    if not diff:
        return {"status": "empty", "topic": topic, "key": key,
                "reason": "no change to record"}
    if len(diff) > CHANGE_LIMIT:
        return {"status": "error", "topic": topic, "key": key,
                "error": (f"the diff is {len(diff)} characters, over the "
                          f"{CHANGE_LIMIT} limit. A change this large is a "
                          f"working tree with debris in it rather than a fix."),
                "bytes": len(diff)}

    topic = resolve_topic(topic)
    record = load(topic)
    for entry in record.get("approaches", []):
        if key not in (entry.get("key"), entry.get("name")):
            continue

        safe = re.sub(r"[^A-Za-z0-9]+", "-", f"{topic}-{entry.get('key')}").strip("-")
        path = _write_path(topic).parent / "changes" / f"{safe}.patch"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(diff + "\n", encoding="utf-8")

        entry["change_patch"] = str(path)
        entry["change_lines"] = sum(1 for line in diff.splitlines()
                                    if line[:1] in "+-" and line[:3] not in ("+++", "---"))
        entry["change_files"] = sorted({m.group(1) for m in
                                        re.finditer(r"^\+\+\+ b/(\S+)", diff,
                                                    re.MULTILINE)})
        entry["change_at"] = time.time()
        _save(record)
        return {"status": "ok", "topic": topic, "key": entry.get("key"),
                "approach": entry.get("name"), "patch": str(path),
                "files": entry["change_files"], "lines": entry["change_lines"],
                "apply": f"git apply {path}"}
    return {"status": "unknown", "topic": topic, "key": key}


def approach_detail(topic: str, key: str) -> Dict[str, Any]:
    """One approach, by key or name. Everything about it, and nothing else.

    The solve step follows the ranked plan one candidate at a time, so it needs
    the detail of the candidate it is ON — not of the four it might reach later.
    Carrying all of them costs context on every task, including the ones where
    the first approach is right, which is most of them.
    """
    record = load(resolve_topic(topic))
    for entry in record.get("approaches", []):
        if key in (entry.get("key"), entry.get("name")):
            return {"status": "ok", "topic": topic, "approach": entry}
    return {"status": "unknown", "topic": topic, "key": key,
            "known": [f"{e.get('key')}:{e.get('name')}"
                      for e in record.get("approaches", [])]}


def dead_approaches(topic: str) -> List[str]:
    """Approaches that must never be proposed again for this topic.

    Anything a real task tried and failed, plus anything the evaluation
    falsified. Deterministic, so a prompt cannot talk its way past it.
    """
    record = load(resolve_topic(topic))
    return sorted({f"{e.get('key') or '?'}:{e.get('name')}"
                   for e in record.get("approaches", [])
                   if e.get("status") in ("failed", "falsified") and e.get("name")})


def topic_skill(topic: str) -> str:
    """The skill this topic's research writes to, or "" if none yet.

    Public so the harness can name it in the solve prompt: the agent should be
    told which skill to load, not made to search for one.
    """
    try:
        record = load(resolve_topic(topic))
    except Exception:
        return ""
    return str((record.get("harvested") or {}).get("skill") or "")


def _topic_skill(record: Dict[str, Any], topic: str) -> str:
    """The ONE skill this topic writes to, decided once and then reused.

    :func:`harvest` runs after every research stage, by design — a stage that is
    truncated otherwise loses what it established. But the name came from the
    record's shared vocabulary, and that vocabulary shifts as approaches
    accumulate, so each call named a slightly different skill. One six-task run
    produced thirty-two: `column-domain`, `column-domain-rule`,
    `based-column-domain`, `cases-column-domain`, `discover-normalize`,
    `discover-normalize-pattern`, `7080-discover-normalize`, and one called
    `check`.

    That is worse than useless. The task's knowledge is smeared across a dozen
    fragments, none of them complete; retrieval returns whichever fragment
    happens to match; and there is no single skill the solve step can be pointed
    at. The run recorded 227 retrievals against 32 skills and still had to read
    the raw record.

    So the name is chosen on the first harvest and pinned in the record. Later
    harvests of the same topic add blocks to that skill instead of founding a
    new one.
    """
    pinned = str((record.get("harvested") or {}).get("skill") or "").strip()
    if pinned:
        return pinned

    name = _subject_of(record, topic)
    record.setdefault("harvested", {})["skill"] = name
    try:
        _save(record)
    except Exception:
        pass
    return name


def _subject_of(record: Dict[str, Any], topic: str) -> str:
    """A subject name for the harvested skill, from the research rather than the task.

    Instance ids like ``pylint-dev__pylint-7080`` name one bug; a skill named
    after it is never retrieved for anything else. The approaches and aspects
    describe the *area*, so their shared vocabulary is a better name.
    """
    words: Dict[str, int] = {}
    for entry in record.get("approaches", []):
        for token in re.split(r"[^a-z0-9]+", str(entry.get("name", "")).lower()):
            if len(token) > 3 and token not in ("this", "that", "with", "from"):
                words[token] = words.get(token, 0) + 1
    for aspect in record.get("aspects", []):
        for token in re.split(r"[^a-z0-9]+", str(aspect.get("name", "")).lower()):
            if len(token) > 3:
                words[token] = words.get(token, 0) + 1

    common = [word for word, count in sorted(words.items(),
                                             key=lambda kv: (-kv[1], kv[0]))
              if count > 1][:3]
    if common:
        # Alphabetical, NOT by frequency.
        #
        # Ordering by count makes the name depend on how many approaches
        # happened to mention each word, which varies run to run. Two runs on
        # the same subsystem produced `ignore-normalize-paths` and
        # `normalize-ignore-paths`: the same three words, two skills, and the
        # carried research split across both instead of accumulating in one.
        # The set of words is the stable thing, so the name is built from the
        # set.
        return _reuse_existing_subject(sorted(common))
    # Fall back to the repository name in the topic, dropping the issue number.
    head = re.split(r"__", str(topic))[0]
    return _slug(head or topic)


def _reuse_existing_subject(words: List[str]) -> str:
    """Reuse a skill already covering these words, whatever order it named them.

    Sorting fixes names minted from here on; this fixes the ones already in the
    store, written before the ordering was stable or by an agent that chose its
    own wording. Without it every existing record would fork a second skill the
    first time it was re-harvested.
    """
    wanted = set(words)
    default = "-".join(words)
    try:
        from phronix import skills

        for existing in skills.iter_skills():
            name = str((existing or {}).get("name") or "")
            if name and set(name.split("-")) == wanted:
                return name
    except Exception:
        pass
    return default


def verify_plan(topic: str) -> Dict[str, Any]:
    """The deterministic corrector for a research record.

    Research is a prediction — "this approach will work, and here is the number
    that says so". This is the check, and like every phronix corrector it is
    arithmetic and file inspection, with no model in the loop: the same record
    yields the same verdict on every machine, forever.

    The five facets, and what each one catches:

    ``assumptions``
        A figure of merit exists, with a direction, a target and a stated way to
        measure it. Gates the rest — nothing below can be judged without it, so
        its absence is ``inconclusive``, not ``fail``.
    ``inputs``
        At least two approaches carry the figure of merit. One measured option is
        not a comparison, however carefully it was described.
    ``constraints``
        A choice was recorded, and it is the argmax of the measured values. This
        catches the specific failure where a model compares options, then selects
        the one it argued for rather than the one that won.
    ``invariants``
        Every deterministic step names a capability. A deterministic step left as
        prose is a step that will be performed differently next time — the exact
        drift the deterministic/judgement split exists to stop.
    ``outputs``
        The achieved figure of merit meets the target. Not the *predicted* one:
        the number the work actually delivered. Research that looked convincing
        and did not hold fails here, which is the whole reason to keep predicted
        and achieved as separate fields.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    facets: List[Dict[str, Any]] = []

    def facet(name: str, verdict: str, detail: str) -> None:
        facets.append({"facet": name, "verdict": verdict, "detail": detail})

    fom = record.get("fom")
    if not fom:
        facet("assumptions", "inconclusive",
              "no figure of merit declared; nothing else can be judged")
        return {"status": "ok", "topic": topic, "verdict": "inconclusive",
                "facets": facets}
    facet("assumptions", "pass",
          f"figure of merit {fom['name']!r} ({fom['direction']}, target "
          f"{fom['target']:g}), measured by: {fom['measure']}")

    approaches = [a for a in record.get("approaches", [])
                  if a.get("source") != "benchmark attempt"]
    scored = [a for a in approaches if fom["name"] in a.get("metrics", {})]
    # Measured means "scored from trials on held-out instances" — the value is
    # written by evaluate_approach, never by the agent asserting it.
    measured = [a for a in scored if a.get("measured")]
    hypothesised = [a for a in approaches
                    if str(a.get("hypothesis", "")).strip()
                    and a.get("source") != "benchmark attempt"]
    # Two ways to satisfy this, because there are two ways to get evidence.
    #
    # A self-built corpus measures approaches before any is implemented, which
    # suits a task with no external judge. When one exists — a benchmark that
    # runs the real tests against the patch — synthesising a second evaluator
    # duplicates it at great cost: measured live, that path produced 16
    # approaches and zero trials, because adding an approach is cheap and the
    # corpus never finished inside the budget.
    #
    # So: measured trials satisfy this outright, and failing that, at least two
    # falsifiable approaches do — with the measurement arriving from the attempt.
    if len(measured) >= 2:
        facet("inputs", "pass",
              f"{len(measured)} approaches scored on {fom['name']!r} from "
              "held-out trials")
    elif len(hypothesised) >= 2:
        facet("inputs", "pass",
              f"{len(hypothesised)} falsifiable approaches recorded; the "
              "measurement comes from the attempt")
    else:
        facet("inputs", "fail",
              f"only {len(hypothesised)} approach(es) carry a hypothesis; at "
              "least 2 are needed so there is something to compare and something "
              "to refute")

    confirmed = [a for a in approaches if a.get("status") == "confirmed"]
    falsified = [a for a in approaches if a.get("status") == "falsified"]
    chosen = record.get("chosen")
    if confirmed:
        facet("constraints", "pass",
              f"{confirmed[0]['name']!r} is confirmed on unseen instances "
              f"({len(falsified)} other approach(es) falsified)")
    elif approaches:
        picked = select(topic)
        facet("constraints", "inconclusive",
              f"none confirmed yet; acting on {picked.get('selected')!r} "
              f"({picked.get('approach_status')}) with "
              f"{len(falsified)} falsified")
    elif scored:
        best = rank(scored, fom["name"], fom["direction"])[0]
        if best["name"] != chosen.get("name"):
            facet("constraints", "fail",
                  f"chose {chosen.get('name')!r} but {best['name']!r} is better on "
                  f"{fom['name']!r} ({best['metrics'][fom['name']]:g})")
        elif not chosen.get("measured"):
            facet("constraints", "fail",
                  f"{chosen['name']!r} is the argmax on {fom['name']!r}, but its "
                  "value was predicted rather than measured — the comparison "
                  "cannot distinguish it from the approach the agent preferred")
        else:
            facet("constraints", "pass",
                  f"{chosen['name']!r} is the argmax on {fom['name']!r}, measured")
    else:
        facet("constraints", "fail",
              f"{chosen.get('name')!r} was chosen but no approach measures "
              f"{fom['name']!r}")

    plan = record.get("plan", [])
    unbuilt = [s["title"] for s in plan
               if s["kind"] == "deterministic" and not s.get("capability")]
    if not plan:
        facet("invariants", "fail", "no plan recorded")
    elif unbuilt:
        facet("invariants", "fail",
              f"{len(unbuilt)} deterministic step(s) have no capability: "
              + ", ".join(unbuilt[:3]))
    else:
        facet("invariants", "pass",
              f"all {len(plan)} step(s) tagged, deterministic ones built")

    # Did the research actually look outward, or only at the file in front of it?
    #
    # Checked rather than trusted, because it is the stage most easily skipped
    # and least visible afterwards: an approach invented from the local code
    # reads exactly like one taken from the project's own issue tracker. Every
    # approach must say where it came from, and at least one must come from
    # outside this checkout — upstream docs, an issue, a commit, a changelog.
    sourced = [a for a in approaches if str(a.get("source", "")).strip()]
    external = [a for a in sourced if _looks_external(str(a.get("source", "")))]
    if not approaches:
        facet("evidence", "fail", "no approaches, so no evidence of research")
    elif not sourced:
        facet("evidence", "fail",
              "no approach records where it came from; an unsourced approach "
              "cannot be checked and will be re-invented next time")
    elif not external:
        facet("evidence", "fail",
              "every approach came from reading this checkout. Consult the "
              "project's own documentation, issues, commits or changelog — for a "
              "known bug the fix or the discussion leading to it is usually "
              "already published")
    else:
        facet("evidence", "pass",
              f"{len(external)} of {len(approaches)} approaches cite an external "
              "source")

    # Was the approach checked against instances it was never shaped against?
    counts = _phase_counts(record)
    missing_phases = [phase for phase in PHASES if not counts.get(phase)]
    confirmed_names = {a["name"] for a in approaches if a.get("status") == "confirmed"}
    tested = {t["approach"] for t in record.get("trials", [])
              if t["phase"] == "test"}
    if not (record.get("corpus") or record.get("instances")):
        facet("trials", "pass",
              "no self-built corpus; approaches are measured by the attempt's own "
              "evaluation, which is a stronger test than instances written by the "
              "same reasoning that produced the approach")
    elif missing_phases:
        facet("trials", "fail",
              f"no task instances for: {', '.join(missing_phases)}. Without an "
              "unseen set, 'it works' means only that it was tuned until it did")
    elif confirmed_names and not (confirmed_names & tested):
        facet("trials", "fail",
              f"{', '.join(sorted(confirmed_names))} was promoted without any "
              "trial on the test instances")
    else:
        facet("trials", "pass",
              f"instances: {counts['train']} train, {counts['validate']} validate, "
              f"{counts['test']} test; {len(tested)} approach(es) tried on the "
              "unseen set")

    achieved = record.get("achieved")
    if not achieved:
        facet("outputs", "inconclusive",
              "the plan has not been executed and measured yet; call "
              "research_record_achieved once it has")
    elif _meets(achieved["value"], fom):
        facet("outputs", "pass",
              f"achieved {achieved['value']:g} against target {fom['target']:g}")
    else:
        facet("outputs", "fail",
              f"achieved {achieved['value']:g}, which misses the target "
              f"{fom['target']:g} ({fom['direction']})")

    verdicts = [f["verdict"] for f in facets]
    overall = ("fail" if "fail" in verdicts
               else "inconclusive" if "inconclusive" in verdicts else "pass")
    return {"status": "ok", "topic": topic, "verdict": overall, "facets": facets}


def record_attempt(topic: str, locations: List[str], fom_value: Optional[float] = None,
                   note: str = "", resolved: bool = False) -> Dict[str, Any]:
    """Record that an attempt touched *locations* and how it scored. Mechanical.

    Called by the harness after every attempt, not by a model. That is the point:
    an exclusion list assembled by asking an agent to remember what it already
    tried is exactly as reliable as its memory of the last hour, which is how a
    run ends up with three byte-identical patches against the same function. The
    files a patch touched and the number the tests returned are both facts on
    disk, so recording them needs no judgement and cannot drift.

    Each distinct set of locations becomes an approach in the record, so a failed
    location is measured against the same figure of merit as any researched
    alternative and :func:`ruled_out` can report it with evidence rather than
    with an opinion.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    key = ", ".join(sorted(locations)) or "(no files changed)"
    log = record.setdefault("attempts_log", [])
    log.append({"locations": sorted(locations), "fom_value": fom_value,
                "resolved": bool(resolved), "note": str(note)[:400],
                "at": time.time()})

    # Mirror it as an approach so the comparison machinery sees it too.
    existing = next((a for a in record["approaches"] if a["name"] == key), None)
    metrics = {}
    fom = record.get("fom")
    if fom and fom_value is not None:
        metrics = {fom["name"]: float(fom_value)}
    if existing:
        existing.setdefault("metrics", {}).update(metrics)
        existing["attempts"] = int(existing.get("attempts", 1)) + 1
    else:
        record["approaches"].append({
            "name": key, "summary": f"attempted by editing {key}",
            "metrics": metrics, "source": "benchmark attempt",
            "tools": [], "attempts": 1, "at": time.time()})
    _save(record)
    return {"status": "ok", "topic": topic, "locations": sorted(locations),
            "attempts_recorded": len(log)}


def ruled_out(topic: str) -> Dict[str, Any]:
    """Locations already tried that did NOT reach the figure of merit.

    The answer to "where should I not look again". Derived from recorded facts,
    so it stays correct however many attempts have run and whatever the agent
    remembers.

    Reports how many distinct locations have failed and how many attempts were
    spent on them, because those two numbers together are the signal that the
    approach — not the execution — is wrong. Several attempts against one
    location says keep looking elsewhere far more clearly than any single failure
    does.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    log = record.get("attempts_log", [])
    fom = record.get("fom")

    failed: Dict[str, Dict[str, Any]] = {}
    worked: List[Dict[str, Any]] = []
    for entry in log:
        key = ", ".join(entry["locations"]) or "(no files changed)"
        met = entry.get("resolved") or (
            fom and entry.get("fom_value") is not None
            and _meets(float(entry["fom_value"]), fom))
        if met:
            worked.append(entry)
            continue
        slot = failed.setdefault(key, {"locations": entry["locations"],
                                       "attempts": 0, "best": None})
        slot["attempts"] += 1
        value = entry.get("fom_value")
        if value is not None:
            slot["best"] = value if slot["best"] is None else max(slot["best"], value)

    entries = sorted(failed.values(), key=lambda s: -s["attempts"])
    return {
        "status": "ok",
        "topic": topic,
        "ruled_out": entries,
        "worked": worked,
        "total_attempts": len(log),
        "advice": (
            f"{len(entries)} location set(s) have failed across {len(log)} "
            "attempt(s). Do not edit them again unless you have new evidence — "
            "look at the code paths around them: the helper being called, the "
            "caller, or where the inputs are normalised."
            if entries else "nothing ruled out yet"),
    }


def status(topic: str) -> Dict[str, Any]:
    """What has been researched for *topic*, and what is still missing.

    Reports the gaps explicitly — an approach with no metrics, a plan whose
    deterministic steps have no capability named — because a half-finished
    research record that looks complete is worse than none: the next session
    trusts it and skips the research.
    """
    topic = resolve_topic(topic)
    record = load(topic)
    approaches = record.get("approaches", [])
    plan = record.get("plan", [])
    unmeasured = [a["name"] for a in approaches if not a.get("metrics")]
    unbuilt = [s["title"] for s in plan
               if s["kind"] == "deterministic" and not s.get("capability")]
    return {
        "status": "ok",
        "topic": topic,
        "approaches": [a["name"] for a in approaches],
        "chosen": (record.get("chosen") or {}).get("name"),
        "steps": len(plan),
        "unmeasured_approaches": unmeasured,
        "deterministic_steps_without_capability": unbuilt,
        "complete": bool(approaches and record.get("chosen") and plan
                         and not unbuilt),
    }


def list_topics() -> List[str]:
    """Every topic with a research record, by slug, across the search roots."""
    found = set()
    for root in _search_roots():
        try:
            found.update(p.stem for p in root.glob("*.json"))
        except OSError:
            continue
    return sorted(found)
