"""Do lessons or capabilities overlap or contradict each other? A deterministic look at the store: it finds what a person or an agent should consolidate, and changes nothing.

A group is {kind: conflict|overlap|crowded, ids, ...}. A group someone decided is fine is kept in <learning>/consolidation_keep.json and not reported again.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from . import capstore, learning

OVERLAP = 0.55            # shared words, of all the words of the smaller text
CONFLICT = 0.4            # about the same thing, but one forbids what the other allows
RULE_OVERLAP = 0.7
CAP_OVERLAP = 0.5
MIN_WORDS = 5
CONFLICT_SAME = 0.5      # two rules contradict only when they are about the same thing, both ways
MIN_SHARED_RULES = 2      # one shared line is a coincidence
CROWDED = 25              # lessons on one capability: too many to read before acting
SHOWN_CHARS = 200
STOP = frozenset("the and for with from that this not was were are but has have into when then than they them its use used using must should can will all any each one only".split())
FORBIDS = re.compile(r"\b(?:never|not|avoid|don't|cannot|must not)\s+([a-z0-9_]{3,})", re.I)
BOILERPLATE = ("becomes a capability", "follow `capability_builder`", "A failed verdict comes here")


def _words(text: str) -> Set[str]:
    return {w for w in re.findall(r"[a-z0-9_]{3,}", text.lower()) if w not in STOP}


def _alike(a: Set[str], b: Set[str]) -> float:
    """How much of the shorter text the longer one repeats: a short rule restated inside a long one is a duplicate."""
    return len(a & b) / max(min(len(a), len(b)), 1)


def _same(a: Set[str], b: Set[str]) -> float:
    """How much two texts share both ways (Jaccard): what "the same subject" or "these two contradict" needs, where a
    short sentence whose few words a long one happens to contain is neither."""
    return len(a & b) / max(len(a | b), 1)


def _forbidden(text: str) -> Set[str]:
    """The word each negative applies to: `never build X` forbids build."""
    return {m.group(1).lower() for m in FORBIDS.finditer(text)} - STOP


def _opposed(x: str, y: str) -> bool:
    """One forbids what the other does."""
    fx, fy = _forbidden(x), _forbidden(y)
    return bool((fx - fy) & _words(y)) or bool((fy - fx) & _words(x))


def _decisions_file() -> Path:
    """The project's consolidation decisions, committed beside its capabilities (<package>/.agents/consolidation_keep.json),
    so every install of the project agrees on what was already judged different on purpose."""
    return Path(capstore.BUNDLED).parent / "consolidation_keep.json"


def decisions() -> List[Dict[str, Any]]:
    try:
        rows = json.loads(_decisions_file().read_text())
    except (OSError, ValueError):
        return []
    return [r if isinstance(r, dict) else {"ids": r, "why": ""} for r in rows]


def _kept() -> Set[str]:
    """Groups judged different on purpose: the project's committed decisions, and this install's older ones."""
    out = {r["ids"] for r in decisions()}
    f = capstore._learning_dir() / "consolidation_keep.json"
    try:
        out |= set(json.loads(f.read_text()))
    except (OSError, ValueError):
        pass
    return out


def _key(ids: Iterable[str]) -> str:
    return "|".join(sorted(ids))


def keep(ids: List[str], why: str) -> Dict[str, Any]:
    """Record that these are different on purpose, so they are not reported again."""
    if len(ids) < 2 or not (why or "").strip():
        return {"status": "error", "error": "name at least two ids and say why they stay apart"}
    key = _key(ids)
    rows = [r for r in decisions() if r["ids"] != key] + [{"ids": key, "why": why.strip()}]
    f = _decisions_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(sorted(rows, key=lambda r: r["ids"]), indent=1) + "\n")
    return {"status": "ok", "kept": key, "why": why, "file": str(f)}


def _groups(pairs: List[Tuple[str, str]]) -> List[List[str]]:
    """Connected ids: a overlaps b and b overlaps c is one thing to consolidate."""
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)
    out: Dict[str, List[str]] = {}
    for x in parent:
        out.setdefault(find(x), []).append(x)
    return [sorted(g) for g in out.values()]


def lessons() -> List[Dict[str, Any]]:
    rows = [r for r in learning.all_lessons().values() if r.get("status") in ("applied", "pending")]
    words = {r["id"]: _words(r["text"]) for r in rows}
    near, opposed = [], []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            wa, wb = words[a["id"]], words[b["id"]]
            if min(len(wa), len(wb)) < MIN_WORDS:
                continue
            like = _alike(wa, wb)
            if like >= CONFLICT and _opposed(a["text"], b["text"]):
                opposed.append((a["id"], b["id"]))
            elif like >= OVERLAP:
                near.append((a["id"], b["id"]))
    by_id = {r["id"]: r for r in rows}
    clash = {i for p in opposed for i in p}
    out = []
    for g in _groups(near + opposed):
        out.append({"kind": "conflict" if clash & set(g) else "overlap", "ids": g, "capabilities": sorted({by_id[i]["capability"] for i in g}),
                    "texts": [by_id[i]["text"][:SHOWN_CHARS] for i in g]})
    counts: Dict[str, List[str]] = {}
    for r in rows:
        counts.setdefault(r["capability"], []).append(r["id"])
    out += [{"kind": "crowded", "ids": sorted(ids), "capabilities": [c], "texts": [f"{len(ids)} lessons on {c}"]} for c, ids in counts.items() if len(ids) > CROWDED]
    return out


RULE_SECTIONS = ("rules", "constraints", "corner cases")


def _rules(skill: str) -> List[str]:
    """The bullets of the sections that state rules (Rules, Constraints, Corner cases, and their subsections): the
    Corrector, Self-heal, What works and quoted sources are procedures and evidence, not rules to compare. A skill
    without those sections is read whole."""
    skill = skill or ""
    picked, inside, any_section = [], False, False
    for line in skill.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() in RULE_SECTIONS
            any_section = any_section or inside
        elif inside and line.startswith("- "):
            picked.append(line)
    lines = [x[2:].strip() for x in (picked if any_section else [x for x in skill.splitlines() if x.startswith("- ")])]
    return [x for x in lines if not any(b in x for b in BOILERPLATE)]



COMMON_MIN = 4            # a rule (nearly word for word) in this many capabilities is standing text, not an overlap


def _own(name: str, rules: List[str]) -> List[str]:
    """Rules with the capability's own name (and its tools named after it) written as SELF: generated text that differs
    only in that name is the same text."""
    pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])")     # the name, also inside name_tool
    return [pat.sub("SELF", x) for x in rules]


def _common(rule_sets: List[List[str]]) -> Set[str]:
    """Rule texts (by their words) found in COMMON_MIN or more capabilities: the shared standing rules and generated
    boilerplate every converted capability carries. Comparing them would report every pair."""
    seen: Dict[str, int] = {}
    for rules in rule_sets:
        for k in {" ".join(sorted(_words(x))) for x in rules}:
            seen[k] = seen.get(k, 0) + 1
    return {k for k, n in seen.items() if n >= COMMON_MIN}


def capabilities() -> List[Dict[str, Any]]:
    """Pairs of capabilities that share rules, cover the same subject, or contradict each other. Only pairs involving
    one of this project's own capabilities: two upstream capabilities are their project's to consolidate."""
    from . import config as _cfg
    upstream = {s.project for s in _cfg.S.upstream}
    raw = []
    for name, (layer, d, meta) in sorted(capstore.all_caps().items()):
        try:
            raw.append((name, layer not in upstream, meta.get("description", ""), _own(name, _rules((d / "SKILL.md").read_text(errors="replace")))))
        except OSError:
            continue
    common = _common([r for _, _, _, r in raw])
    # Each rule's words once per capability, not once per pair: the same result in a tenth of the time.
    caps = [(name, own, desc, [(x, w) for x in rules for w in [_words(x)] if len(w) >= MIN_WORDS and " ".join(sorted(w)) not in common])
            for name, own, desc, rules in raw]
    out = []
    for i, (a, own_a, da, ra) in enumerate(caps):
        for b, own_b, db, rb in caps[i + 1:]:
            if not (own_a or own_b):
                continue
            same, clash = [], []
            for x, wx in ra:
                for y, wy in rb:
                    like = _alike(wx, wy)
                    if like >= RULE_OVERLAP and _same(wx, wy) >= CONFLICT_SAME and _opposed(x, y):
                        clash.append(f"{a}: {x[:SHOWN_CHARS]} | {b}: {y[:SHOWN_CHARS]}")
                    elif like >= RULE_OVERLAP:
                        same.append(x[:SHOWN_CHARS])
            wa, wb = _words(da.split(". ")[0]), _words(db.split(". ")[0])      # what follows the first sentence says when to load it, in the same words everywhere
            subject = min(len(wa), len(wb)) >= MIN_WORDS and _same(wa, wb) >= CAP_OVERLAP
            if clash:
                out.append({"kind": "conflict", "ids": [a, b], "texts": clash[:3]})
            elif len(same) >= MIN_SHARED_RULES or subject:
                out.append({"kind": "overlap", "ids": [a, b], "texts": same[:3] or [da[:SHOWN_CHARS], db[:SHOWN_CHARS]]})
    return out


def report() -> Dict[str, Any]:
    """What needs consolidating now: groups nobody decided on and nobody was asked about yet, and the open questions."""
    return unkept({"lessons": lessons(), "capabilities": capabilities(), "checked": round(time.time(), 1)})


def unkept(rep: Dict[str, Any]) -> Dict[str, Any]:
    """A report without the groups someone has since kept, asked about or resolved (a lesson of it is no longer in force), so the page does
    not show a decided group until the next check; with the questions waiting for the user."""
    kept, asked, live = _kept(), {_key(q["ids"]) for q in questions()}, _in_force()
    merging = {i for r in learning.all_lessons().values() if r.get("status") == "pending" and r.get("supersedes")       # a proposed merge waits in the panel
               for i in ([r["supersedes"]] if isinstance(r["supersedes"], str) else r["supersedes"])}
    lg = [g for g in rep.get("lessons", []) if _key(g["ids"]) not in kept | asked and sum(i in live and i not in merging for i in g["ids"]) >= 2]
    cg = [g for g in rep.get("capabilities", []) if _key(g["ids"]) not in kept]
    return {**rep, "lessons": lg, "capabilities": cg, "questions": questions()}


# ---------------------------------------------------------------- questions: a conflict the agent cannot settle, for the user to answer
ACTIONS = ("keep", "supersede", "merge", "drop")


def _in_force() -> Set[str]:
    return {i for i, r in learning.all_lessons().items() if r.get("status") in ("applied", "pending")}


def _qfile() -> Path:
    return capstore._learning_dir() / "consolidation_questions.json"


def _qall() -> List[Dict[str, Any]]:
    try:
        return json.loads(_qfile().read_text())
    except (OSError, ValueError):
        return []


def _qsave(qs: List[Dict[str, Any]]) -> None:
    _qfile().write_text(json.dumps(qs, indent=1))


def questions(status: str = "open") -> List[Dict[str, Any]]:
    """Questions with that status; an open one whose lessons were resolved meanwhile is no longer asked."""
    live = _in_force()
    return [q for q in _qall() if q.get("status") == status and (status != "open" or sum(i in live for i in q["ids"]) >= 2)]


def _check_option(o: Dict[str, Any], ids: List[str]) -> str:
    do = o.get("do")
    if do not in ACTIONS:
        return f"option {o.get('label')!r}: do is one of {', '.join(ACTIONS)}"
    if not (o.get("label") or "").strip():
        return "every option needs a label: what it means, in a few words"
    if do == "supersede" and o.get("winner") not in ids:
        return f"option {o['label']!r}: supersede needs winner, one of {ids}"
    if do == "merge" and (not (o.get("text") or "").strip() or o.get("capability") not in capstore.all_caps()):
        return f"option {o['label']!r}: merge needs the whole merged text and a known capability"
    if do == "drop" and (not o.get("drop") or not set(o["drop"]) <= set(ids)):
        return f"option {o['label']!r}: drop needs drop, the lessons of this group that are wrong"
    return ""


def ask(ids: List[str], question: str, options: List[Dict[str, Any]], recommended: int, why: str) -> Dict[str, Any]:
    """Ask the user to settle a group: 2-4 options, each a concrete action, one recommended with the reason."""
    rows = learning.all_lessons()
    ids = sorted(set(ids))
    bad = [i for i in ids if i not in rows]
    if len(ids) < 2 or bad:
        return {"status": "error", "error": f"name at least two known lessons; unknown: {bad}"}
    if not (question or "").strip() or not (why or "").strip():
        return {"status": "error", "error": "a question needs its text and why the recommended option holds"}
    if not 2 <= len(options or []) <= 4:
        return {"status": "error", "error": "give 2 to 4 options"}
    errs = [e for e in (_check_option(o, ids) for o in options) if e]
    if errs:
        return {"status": "error", "error": "; ".join(errs)}
    if not 0 <= int(recommended) < len(options):
        return {"status": "error", "error": "recommended is the index of one of the options"}
    qs = [q for q in _qall() if not (q.get("status") == "open" and _key(q["ids"]) == _key(ids))]     # a new question on a group replaces the old
    q = {"id": "Q-" + uuid.uuid4().hex[:8], "ids": ids, "question": question.strip(), "why": why.strip(), "recommended": int(recommended),
         "options": [{k: v for k, v in o.items() if k in ("label", "do", "winner", "text", "capability", "drop")} for o in options],
         "lessons": {i: {"text": rows[i]["text"], "capability": rows[i]["capability"], "status": rows[i]["status"]} for i in ids},
         "status": "open", "ts": round(time.time(), 1)}
    _qsave(qs + [q])
    return {"status": "ok", "id": q["id"], "note": "the user answers it in the Lessons panel; the group is not reported again meanwhile"}


def answer(qid: str, choice: Optional[int] = None, note: str = "", by: str = "") -> Dict[str, Any]:
    """The user's answer: an option is applied at once; free text (no choice) goes back to the consolidation agent."""
    qs = _qall()
    q = next((x for x in qs if x["id"] == qid), None)
    if not q or q.get("status") != "open":
        return {"status": "error", "error": f"no open question {qid}"}
    if choice is None:
        if not (note or "").strip():
            return {"status": "error", "error": "pick an option or write your answer"}
        q.update(status="for_agent", answer={"note": note.strip(), "by": by, "ts": round(time.time(), 1)})
        _qsave(qs)
        return {"status": "for_agent", "id": qid, "question": q}
    o = (q["options"] or [])[int(choice)]
    why = note.strip() or o["label"]
    if o["do"] == "keep":
        r = keep(q["ids"], why)
    elif o["do"] == "supersede":
        r = learning.retire(q["ids"], by, winner=o["winner"], note=why)
        w = learning.all_lessons().get(o["winner"])
        if w and w["status"] == "pending":
            learning.decide(o["winner"], True, by)
    elif o["do"] == "drop":
        r = learning.retire(o["drop"], by, note=why)
    else:
        m = learning.merge(q["ids"], o["text"], o["capability"], why, by)
        r = learning.decide(m["id"], True, by) if m.get("status") == "ok" else m
    if r.get("status") == "error":
        return r
    q.update(status="answered", answer={"choice": int(choice), "label": o["label"], "note": note.strip(), "by": by, "ts": round(time.time(), 1)})
    _qsave(qs)
    return {"status": "ok", "id": qid, "applied": o["do"], "result": r}


def close(qid: str, what: str) -> Dict[str, Any]:
    """The agent acted on the user's own answer."""
    qs = _qall()
    q = next((x for x in qs if x["id"] == qid), None)
    if not q or q.get("status") != "for_agent":
        return {"status": "error", "error": f"{qid} is not waiting for the agent"}
    q.update(status="answered", done=what)
    _qsave(qs)
    return {"status": "ok", "id": qid}


# ---------------------------------------------------------------- the background consolidation runs (phronix.engine.background)
def fingerprint(rep: Dict[str, Any], part: str) -> str:
    """Identity of the work open in one part: its groups and, for lessons, the answers the user wrote for the agent. A
    background consolidation run starts only when this changes (or when forced)."""
    import hashlib
    ids = sorted(",".join(sorted(g["ids"])) for g in rep.get(part) or [])
    if part == "lessons":
        ids += sorted(q["id"] for q in questions("for_agent"))
    return hashlib.sha1("|".join(ids).encode()).hexdigest()[:12] if ids else ""


ASK = {
    "lessons": ("Consolidate the lessons. First call consolidation_answers: act on each answer the user wrote, then "
                "consolidation_close it. Then call consolidation_report and read every member of each lessons group in full "
                "with lesson_get. For overlapping lessons, propose one merged lesson with lesson_merge. Lessons that "
                "contradict each other, or that you cannot settle alone: do not pick one yourself - call consolidation_ask "
                "with one plain question, 2-4 concrete options (keep, supersede, merge, drop) and the one you recommend "
                "with its evidence, so the user can answer it in the Lessons panel. Every conflict group must end as a "
                "question, a merge or a keep, never only in your report. A group that is different on purpose: consolidation_keep."),
    "capabilities": ("Consolidate the capabilities. Call consolidation_report and read the capabilities groups, then each "
                     "capability with capability_get. For an overlap, propose moving what is shared to the better home "
                     "with capability_update; never disable one. Conflicting rules: do not pick one; list them in your "
                     "report for the user. A group that is different on purpose: consolidation_keep."),
}
