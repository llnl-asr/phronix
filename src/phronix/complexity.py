"""Task complexity assessment — choosing the model level from measurable signals.

Agents declare a capability level (``level_1`` … ``level_4``) rather than a model
id. The question this module answers is: **given what an agent's scope has grown
into, which level does it now need?**

That question has an answer that changes over time, which is the whole point. As
skills accumulate rules, as pitfalls pile up, as capabilities absorb the
deterministic parts, the amount of *judgment* an agent must supply moves — usually
up as knowledge accumulates, and down as that knowledge is converted into tools.
An agent pinned at the level it was written with drifts away from what it needs.

The signals, and why each one points where it does
---------------------------------------------------

**reasoning_demand** — rules and instructions across the agent's skills. Every
rule is a constraint that has to be weighed against the others in context.
Weighing constraints is thinking, and thinking is what a stronger model buys.
Rules count double: an instruction says what to do next, a rule says what would
make an otherwise-reasonable action wrong.

**failure_surface** — pitfalls and lessons across those skills. A subject with
many recorded traps is one where the naive path is wrong in ways that are not
locally visible. Recognising which trap applies is judgment, not lookup, so a
large failure surface raises the requirement.

**integration_breadth** — distinct subjects plus outgoing references. Holding two
subjects and the interaction between them is materially harder than following one
procedure, and cross-references are exactly where the interactions live.

**instruction_load** — prose in the agent's own sections. A long prompt has more
internal structure to keep consistent.

**unverified_fraction** — subjects with no authored corrector. Where a claim can
be checked, an agent can act and verify. Where it cannot, the agent has to be
right by reasoning, which is the expensive kind of right.

**tool_coverage** — the fraction of the agent's tools that are MCP capabilities.
This is the only signal that pushes *down*, and it is the lever the framework is
built around: every deterministic procedure turned into a tool is judgment the
model no longer has to supply. An agent that mostly calls well-specified tools is
doing orchestration, and orchestration is a ``level_1`` job.

Everything here is deterministic — counts and ratios over files, no model in the
loop — so the same store yields the same assessment on every machine, and a
recommendation can be explained by pointing at the numbers that produced it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

#: Weights. They sum to 1.0 over the raising signals; ``tool_coverage`` is
#: subtracted, so a fully tool-driven agent can fall a full band.
WEIGHTS: Dict[str, float] = {
    "reasoning_demand": 0.30,
    "failure_surface": 0.25,
    "unverified_fraction": 0.20,
    "integration_breadth": 0.15,
    "instruction_load": 0.10,
    "tool_coverage": -0.25,
}

#: Saturation points: the count at which a signal is considered fully loaded.
#: Chosen so a typical single-subject agent lands mid-range rather than pinned at
#: either end, where the signal would stop discriminating.
SATURATION: Dict[str, float] = {
    "weighted_blocks": 40.0,    # rules*2 + instructions
    "failure_entries": 15.0,    # pitfalls + lessons
    "integration_units": 10.0,  # subjects + outgoing references
    "prose_chars": 8000.0,
}

#: Score bands. A band boundary is a judgement call; these are set so that a
#: purely mechanical agent lands in level_1 and an agent spanning several
#: unverified subjects with many recorded traps lands in level_4.
BANDS = ((0.25, "level_1"), (0.45, "level_2"), (0.70, "level_3"))
TOP_LEVEL = "level_4"

#: Reasoning-effort hint, derived from the same score.
EFFORT_BANDS = ((0.30, "low"), (0.60, "medium"), (0.85, "high"))
TOP_EFFORT = "max"

#: The floor an agent's declared ``intrinsic:`` puts under its level.
#:
#: The signals above measure complexity *derived from scope* — how much recorded
#: knowledge the agent has to hold. That is most of the picture and it is not all
#: of it: some agents are hard because of what they DO, not what they load. A
#: planner synthesising a multi-step plan from sparse information is doing
#: level_4 work while declaring one skill and calling well-specified tools, and a
#: purely scope-based measure would confidently demote it.
#:
#: So the template declares the irreducible reasoning its *function* requires, and
#: the assessment takes whichever is higher. Measurement can raise a level above
#: the declaration; it can never lower it below.
INTRINSIC_FLOOR = {
    "low": "level_1",        # orchestration, dispatch, mechanical checks
    "moderate": "level_2",   # routine reasoning over known material
    "high": "level_3",       # diagnosis, judgment under uncertainty
    "max": "level_4",        # synthesis, planning, cross-cutting design
}

_LEVEL_ORDER = ("level_1", "level_2", "level_3", "level_4")


def _higher(left: str, right: str) -> str:
    try:
        return left if _LEVEL_ORDER.index(left) >= _LEVEL_ORDER.index(right) else right
    except ValueError:
        return left


def _saturate(value: float, ceiling: float) -> float:
    """Map a count onto 0..1, flattening above *ceiling*.

    Linear-with-clamp rather than a smooth curve: the numbers are shown to users
    alongside the verdict, and a reader can verify a clamp by eye.
    """
    if ceiling <= 0:
        return 0.0
    return max(0.0, min(1.0, value / ceiling))


def level_for(score: float) -> str:
    for threshold, level in BANDS:
        if score < threshold:
            return level
    return TOP_LEVEL


def effort_for(score: float) -> str:
    for threshold, effort in EFFORT_BANDS:
        if score < threshold:
            return effort
    return TOP_EFFORT


def signals_for(
    skills_used: List[Dict[str, Any]],
    tools: List[str],
    prose_chars: int,
) -> Dict[str, Any]:
    """Compute the raw counts and the normalised signals. Pure and inspectable."""
    from phronix.verification import covers

    rules = sum(1 for s in skills_used for b in s["blocks"] if b["kind"] == "rule")
    instructions = sum(1 for s in skills_used for b in s["blocks"]
                       if b["kind"] == "instruction")
    references = sum(1 for s in skills_used for b in s["blocks"] if b["kind"] == "reference")
    pitfalls = sum(1 for s in skills_used for b in s["lesson_blocks"]
                   if b["kind"] == "pitfall")
    lessons = sum(1 for s in skills_used for b in s["lesson_blocks"] if b["kind"] == "lesson")

    unverified = [s["name"] for s in skills_used if not covers("skill", s["name"])]
    mcp_tools = [t for t in tools if t.startswith("mcp__")]

    raw = {
        "skills": len(skills_used),
        "rules": rules,
        "instructions": instructions,
        "references": references,
        "pitfalls": pitfalls,
        "lessons": lessons,
        "tools": len(tools),
        "mcp_tools": len(mcp_tools),
        "unverified_subjects": unverified,
        "prose_chars": prose_chars,
    }

    signals = {
        # Rules weigh double: an instruction says what to do next, a rule says
        # what would make an otherwise-reasonable action wrong.
        "reasoning_demand": _saturate(rules * 2 + instructions,
                                      SATURATION["weighted_blocks"]),
        "failure_surface": _saturate(pitfalls + lessons, SATURATION["failure_entries"]),
        "integration_breadth": _saturate(len(skills_used) + references,
                                         SATURATION["integration_units"]),
        "instruction_load": _saturate(prose_chars, SATURATION["prose_chars"]),
        "unverified_fraction": (len(unverified) / len(skills_used)) if skills_used else 0.0,
        # Guard the empty case: an agent with no tools has no tool coverage, but
        # 0/0 must not read as "fully covered" and discount its requirement.
        "tool_coverage": (len(mcp_tools) / len(tools)) if tools else 0.0,
    }
    return {"raw": raw, "signals": signals}


def score_from(signals: Dict[str, float]) -> float:
    total = sum(WEIGHTS[name] * value for name, value in signals.items() if name in WEIGHTS)
    return max(0.0, min(1.0, total))


def _explain(signals: Dict[str, float], raw: Dict[str, Any]) -> List[str]:
    """Human-readable drivers, largest contribution first.

    A recommendation nobody can interrogate gets overridden or ignored; naming the
    numbers that produced it is what makes it reviewable.
    """
    contributions = sorted(
        ((WEIGHTS[name] * value, name, value) for name, value in signals.items()
         if name in WEIGHTS),
        key=lambda t: -abs(t[0]),
    )
    detail = {
        "reasoning_demand": lambda: f"{raw['rules']} rules + {raw['instructions']} instructions",
        "failure_surface": lambda: f"{raw['pitfalls']} pitfalls + {raw['lessons']} lessons",
        "integration_breadth": lambda: f"{raw['skills']} subjects + {raw['references']} references",
        "instruction_load": lambda: f"{raw['prose_chars']} chars of prompt",
        "unverified_fraction": lambda: f"{len(raw['unverified_subjects'])}/{raw['skills']} subjects unverified",
        "tool_coverage": lambda: f"{raw['mcp_tools']}/{raw['tools']} tools are MCP capabilities",
    }
    return [
        f"{'+' if contribution >= 0 else '-'}{abs(contribution):.3f}  {name} "
        f"({value:.2f}) — {detail[name]()}"
        for contribution, name, value in contributions if abs(contribution) >= 0.001
    ]


def assess_agent(name: str) -> Dict[str, Any]:
    """Assess one agent and recommend a level. Deterministic and explainable."""
    from phronix.agent_templates import load_common_sections, load_template
    from phronix.layers import agent_templates
    from phronix.skills import get as get_skill

    path = agent_templates().get(f"{name}.yaml")
    if path is None:
        return {"status": "not_found", "error": f"no agent template named {name!r}"}
    try:
        template = load_template(path, load_common_sections())
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    skills_used = [s for s in (get_skill(n) for n in template.get("skills") or [])
                   if s is not None]
    prose = sum(len(section["body"]) for section in template["sections"])
    measured = signals_for(skills_used, template.get("tools") or [], prose)
    score = score_from(measured["signals"])
    from_scope = level_for(score)

    intrinsic = str(template.get("intrinsic") or "moderate").lower()
    floor = INTRINSIC_FLOOR.get(intrinsic, "level_2")
    recommended = _higher(from_scope, floor)
    declared = str(template["model_level"])

    drivers = _explain(measured["signals"], measured["raw"])
    if recommended == floor and floor != from_scope:
        drivers.insert(0, f" floor  intrinsic={intrinsic} — the agent's function requires "
                          f"{floor} regardless of scope (scope alone implied {from_scope})")

    return {
        "status": "ok",
        "agent": name,
        "declared_level": declared,
        "recommended_level": recommended,
        "level_from_scope": from_scope,
        "intrinsic": intrinsic,
        "intrinsic_floor": floor,
        "drift": declared != recommended,
        "score": round(score, 3),
        "recommended_effort": effort_for(score),
        "declared_effort": template.get("effort", ""),
        "raw": measured["raw"],
        "signals": {k: round(v, 3) for k, v in measured["signals"].items()},
        "drivers": drivers,
    }


def assess_task(
    description: str,
    skills_named: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assess an ad-hoc task rather than a defined agent.

    Used when dispatching work that has no agent of its own: name the subjects it
    touches and the tools available, and get the level that scope implies.
    """
    from phronix.skills import get as get_skill, search

    names = list(skills_named or [])
    if not names:
        found = search(description, max_results=4)
        names = [r["skill"] for r in found.get("results", [])]

    skills_used = [s for s in (get_skill(n) for n in names) if s is not None]
    measured = signals_for(skills_used, tools or [], len(description))
    score = score_from(measured["signals"])
    return {
        "status": "ok",
        "task": description,
        "subjects": [s["name"] for s in skills_used],
        "recommended_level": level_for(score),
        "recommended_effort": effort_for(score),
        "score": round(score, 3),
        "raw": measured["raw"],
        "signals": {k: round(v, 3) for k, v in measured["signals"].items()},
        "drivers": _explain(measured["signals"], measured["raw"]),
    }


def reassess_all() -> Dict[str, Any]:
    """Assess every agent and report which have drifted from their declared level.

    Run this after any session that grew a skill, recorded lessons, or added a
    capability — those are exactly the events that move an agent's requirement.
    Growth in rules and pitfalls pushes it up; converting procedures into tools
    pushes it down.
    """
    from phronix.layers import agent_templates

    results = [assess_agent(Path(filename).stem) for filename in sorted(agent_templates())]
    ok = [r for r in results if r.get("status") == "ok"]
    drifted = [r for r in ok if r["drift"]]
    return {
        "status": "ok",
        "assessed": len(ok),
        "drifted": len(drifted),
        "drift": [
            {"agent": r["agent"], "declared": r["declared_level"],
             "recommended": r["recommended_level"], "score": r["score"],
             "top_driver": r["drivers"][0] if r["drivers"] else ""}
            for r in drifted
        ],
        "all": ok,
        "next": ("Update each drifted agent with agent_define(model_level=...) — but read "
                 "its drivers first. A rise usually means the subject accumulated rules and "
                 "pitfalls; a fall usually means enough of it became MCP tools, which is the "
                 "outcome to aim for."
                 if drifted else "Every agent's declared level matches its assessed scope."),
    }


def agents_using(skill_name: str) -> List[str]:
    """Which agents declare *skill_name* — i.e. whose complexity a change affects."""
    from phronix.agent_templates import load_common_sections, load_template
    from phronix.layers import agent_templates

    common = load_common_sections()
    out: List[str] = []
    for filename, path in sorted(agent_templates().items()):
        try:
            template = load_template(path, common)
        except Exception:
            continue
        if skill_name in (template.get("skills") or []):
            out.append(template["name"])
    return out


def impact_of(skill_name: str) -> Dict[str, Any]:
    """After a change to *skill_name*, report which agents may now need a different level.

    This is what closes the self-learning loop: a lesson recorded into a skill
    changes the judgment burden of every agent that loads it, and without this the
    agent keeps running at whatever level it was written with.
    """
    affected = agents_using(skill_name)
    assessments = [assess_agent(name) for name in affected]
    drifted = [a for a in assessments if a.get("status") == "ok" and a["drift"]]
    return {
        "skill": skill_name,
        "agents_affected": affected,
        "level_drift": [
            {"agent": a["agent"], "declared": a["declared_level"],
             "recommended": a["recommended_level"]}
            for a in drifted
        ],
        "note": ("These agents load this subject and their assessed level no longer "
                 "matches what they declare." if drifted else
                 "No agent's level changed as a result of this."),
    }
